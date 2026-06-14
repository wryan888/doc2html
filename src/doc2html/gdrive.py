"""Google Drive 小工具（可選）：OAuth 服務、找/建資料夾、上傳/更新檔案。

抽自 DocLib 與 LineArc 共用的那段 Drive 流程，收進 doc2html 這個生態系共用函式庫，
消除兩處重複。**與核心轉換器無關**，需 `pip install 'doc2html[gdrive]'` 才有 google 套件。

沿用 drive.file 最小權限。憑證/ token 路徑由呼叫端傳入（各專案用各自的環境變數）。
無頭環境（VM 常駐）請傳 interactive=False：token 失效時拋明確錯誤而非開瀏覽器。
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


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


def folder_id(svc, name: str) -> str:
    """取得（或建立）指定名稱的資料夾，回傳 ID。"""
    q = (f"name='{name}' and "
         "mimeType='application/vnd.google-apps.folder' and trashed=false")
    items = svc.files().list(
        q=q, spaces="drive", fields="files(id)").execute().get("files", [])
    if items:
        return items[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    return svc.files().create(body=meta, fields="id").execute()["id"]


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
