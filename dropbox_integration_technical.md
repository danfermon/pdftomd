# Dropbox Integration: Technical Specification

## 1. Authentication & Security
The integration leverages the official **Dropbox API v2** via the `dropbox` Python SDK.

### 1.1. Credentials
- **Mechanism**: OAuth 2.0.
- **Environment Variable**: `DROPBOX_ACCESS_TOKEN` (stored in `.env`).
- **Token Type**: Currently using a *App Key/Secret* generated Access Token. For production resilience, we recommend implementing a *Refresh Token* flow to handle token expiration automatically.

### 1.2. Scopes (Least Privilege)
The application requires the following specific scopes enforced at the Dropbox App Console level:
- `account_info.read`: To verify identity and connection status.
- `files.metadata.read`: To traverse directories and list file attributes (Discovery).
- `files.content.read`: To download file streams for content extraction (RAG Ingestion).

## 2. Discovery Service (`services/discovery.py`)
This microservice maps the remote file system to a local inventory without downloading content (metadata-only sync).

### 2.1. Traversal Logic
- **Endpoint**: `dbx.files_list_folder('', recursive=True)`.
- **Recursive Mode**: Enabled to scan the entire tree from the App root.
- **Pagination**: Implements `dbx.files_list_folder_continue(cursor)` to handle large directories. The `cursor` token ensures we fetch subsequent batches of entries reliably.

### 2.2. Metadata Mapping
Remote Dropbox `FileMetadata` objects are mapped to our internal schema:

| Dropbox Attribute | Internal Field | Description |
| :--- | :--- | :--- |
| `id` | `dropbox_id` | Immutable unique identifier (e.g., `id:a4ayc_80_OEAAAAAAAAAXw`). Used as Primary Key for updates. |
| `path_display` | `path` | Human-readable path. normalized to standard separators. |
| `server_modified` | `dropbox_modified` | ISO 8601 timestamp. Critical for version control and incremental sync. |
| `size` | `size_bytes` | File size in bytes. Used for quota and heuristics (e.g., skip files > 50MB). |
| `content_hash` | `content_hash` | Block-based SHA-256 hash provided by Dropbox. Used to detect content changes without downloading. |

## 3. Content Access & Ingestion
Content is accessed strictly on-demand or during the ingestion phase.

### 3.1. Download Strategy
- **Endpoint**: `dbx.files_download(path)`.
- **Method**: Streaming download directly to memory (for small files) or temp disk (for large PDFs) to minimize memory footprint.
- **Concurrency**: Not currently implemented (sequential processing). Future implementations should use `batch` endpoints for high-volume ingestion.

## 4. Error Handling
- **AuthError**: Detects invalid/expired tokens. Triggers a critical alert.
- **BadInputError**: Previously encountered due to missing Scopes. Handled by validating scopes pre-execution.
- **Rate Limiting**: The underlying SDK handles basic backoff. Application logic must respect `Retry-After` headers if massive scanning occurs.

## 5. Artifacts
- **Inventory**: `data/inventory.csv` (Intermediate state).
- **Database**: `documents` table in PostgreSQL (Final state, enriched with ACLs).
