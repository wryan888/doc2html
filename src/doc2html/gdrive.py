"""Google Drive 小工具（可選）：OAuth 服務、找/建資料夾、上傳/更新檔案。

抽自 DocLib 與 LineArc 共用的那段 Drive 流程，收進 doc2html 這個生態系共用函式庫，
消除兩處重複。**與核心轉換器無關**，需 `pip install 'doc2html[gdrive]'` 才有 google 套件。

沿用 drive.file 最小權限。憑證/ token 路徑由呼叫端傳入（各專案用各自的環境變數）。
無頭環境（VM 常駐）請傳 interactive=False：token 失效時拋明確錯誤而非開瀏覽器。
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
# Research inbox 掃描/搬移（D1 Drive API / D2 VM）需讀寫使用者 Drive 上既有檔案
RESEARCH_SCOPES = ["https://www.googleapis.com/auth/drive"]


def service(token_path: str | Path, credentials_path: str | Path,
            *, scopes: list[str] | None = None, interactive: bool = False):
    """建立 Drive API service。

    interactive=True：token 失效時開瀏覽器重新授權（有瀏覽器的 Mac）。
    interactive=False：失效時拋 RuntimeError（無頭 VM）——請在 Mac 重授後把新 token 複製過去。
    """
    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "doc2html.gdrive 需要 google 套件，請執行：pip install 'doc2html[gdrive]'"
        ) from exc

    scopes = scopes or DEFAULT_SCOPES
    token_path = Path(token_path)
    credentials_path = Path(credentials_path)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if creds and creds.valid:
        return build("drive", "v3", credentials=creds)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            return build("drive", "v3", credentials=creds)
        except RefreshError:
            creds = None  # 被撤銷/過期，需重新授權

    if not interactive:
        raise RuntimeError(
            "Drive 授權失效且為非互動環境。請在有瀏覽器的機器重新授權後，"
            f"把新的 token 複製到 {token_path}。")
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not credentials_path.exists():
        raise RuntimeError(f"找不到 OAuth 憑證：{credentials_path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds)


def _esc_q(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def folder_id(svc, name: str) -> str:
    """取得（或建立）指定名稱的資料夾，回傳 ID。"""
    q = (f"name='{_esc_q(name)}' and "
         "mimeType='application/vnd.google-apps.folder' and trashed=false")
    items = svc.files().list(
        q=q, spaces="drive", fields="files(id)").execute().get("files", [])
    if items:
        return items[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    return svc.files().create(body=meta, fields="id").execute()["id"]


def folder_id_in_parent(svc, parent_id: str, name: str, *, create: bool = True) -> str:
    """在 parent 下找（或建立）子資料夾。"""
    q = (
        f"name='{_esc_q(name)}' and '{parent_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    items = svc.files().list(q=q, spaces="drive", fields="files(id)").execute().get("files", [])
    if items:
        return items[0]["id"]
    if not create:
        raise FileNotFoundError(f"Drive 資料夾不存在：{name}（parent={parent_id}）")
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    return svc.files().create(body=meta, fields="id").execute()["id"]


def ensure_folder_path(svc, root_id: str, parts: list[str]) -> str:
    """自 root_id 起依序建立/解析子資料夾路徑，回傳最末層 ID。"""
    cur = root_id
    for part in parts:
        cur = folder_id_in_parent(svc, cur, part)
    return cur


def find_named_folder(svc, name: str, *, parent_id: str | None = None) -> str | None:
    """依名稱找資料夾；parent_id 限定父層（None=My Drive 根下搜尋）。"""
    q = f"name='{_esc_q(name)}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    items = svc.files().list(
        q=q, spaces="drive", fields="files(id,name)", pageSize=10,
    ).execute().get("files", [])
    return items[0]["id"] if items else None


def iter_folder_files(
    svc,
    folder_id: str,
    *,
    skip_dirs: set[str] | None = None,
    rel_prefix: tuple[str, ...] = (),
):
    """遞迴列出資料夾內所有非資料夾檔案。yield (file_meta, rel_parts)。"""
    skip_dirs = skip_dirs or set()
    q = f"'{folder_id}' in parents and trashed=false"
    page_token = None
    while True:
        resp = svc.files().list(
            q=q,
            spaces="drive",
            fields="nextPageToken, files(id,name,mimeType,modifiedTime,size,parents)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                if f["name"] in skip_dirs or f["name"].startswith("."):
                    continue
                yield from iter_folder_files(
                    svc, f["id"], skip_dirs=skip_dirs, rel_prefix=rel_prefix + (f["name"],),
                )
            else:
                if f["name"].startswith("."):
                    continue
                yield f, rel_prefix
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def download_file(svc, file_id: str, dest: str | Path) -> Path:
    """下載 Drive 檔案到本機路徑。"""
    from googleapiclient.http import MediaIoBaseDownload
    import io

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = svc.files().get_media(fileId=file_id)
    with io.FileIO(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return dest


def move_file(svc, file_id: str, *, add_parent: str, remove_parent: str | None = None) -> dict:
    """移動檔案到新 parent（Drive 上 inbox→archive）。"""
    kwargs = {"fileId": file_id, "addParents": add_parent, "fields": "id, parents"}
    if remove_parent:
        kwargs["removeParents"] = remove_parent
    return svc.files().update(**kwargs).execute()


def upload(svc, parent_id: str, path: str | Path, *, existing_id: str | None = None,
           mimetype: str | None = None, fields: str = "id, webViewLink") -> dict:
    """上傳新檔（existing_id=None）或更新既有檔（給 existing_id）。回傳 API 回應 dict。"""
    from googleapiclient.http import MediaFileUpload
    path = Path(path)
    media = MediaFileUpload(str(path), mimetype=mimetype, resumable=True)
    if existing_id:
        req = svc.files().update(fileId=existing_id, media_body=media, fields=fields)
    else:
        meta = {"name": path.name, "parents": [parent_id]}
        req = svc.files().create(body=meta, media_body=media, fields=fields)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp
