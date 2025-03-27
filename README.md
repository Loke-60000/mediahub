# Media Hub API

Minimal API for downloading videos (primarily YouTube via yt-dlp), uploading files, and converting media formats using FastAPI.

## Installation

### Option 1: Miniconda + Pip

1.  **Create Conda Environment:**
    ```bash
    conda create --name mediahub python=3.10 -y
    conda activate mediahub
    ```

2.  **Install Dependencies:**
    (Ensure you have a `requirements.txt` file in the project root)
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If `requirements.txt` does not exist, you'll need to create it based on the project's imports or use `pip freeze > requirements.txt` if dependencies are already installed in an environment.)*

3.  **Environment Variables:**
    Copy `.env.example` to `.env` (if available) or create a `.env` file based on the provided `.env` content and configure as needed. Ensure `TEMP_DIR` exists or is writable.

### Option 2: Docker

1.  **Build Docker Image:**
    ```bash
    docker build -t mediahub-api .
    ```

2.  **Environment Variables:**
    Ensure you have a `.env` file in the project root configured as needed.

## Running the Application

### Development Server (using Miniconda/Pip setup)

1.  Make sure the conda environment is active (`conda activate mediahub`).
2.  Run the development server script:
    ```bash
    ./run-dev.sh
    ```
    The API will typically be available at `http://0.0.0.0:8000` (or as configured in `.env`).

### Docker Container

1.  Run the container, mapping the port, mounting the temporary directory volume, and passing the environment file:
    ```bash
    # Replace /path/on/host with an actual directory on your host machine
    # This directory will store temporary downloads and converted files
    docker run -p 8000:8000 -v /path/on/host:/tmp/youtube-dl --env-file .env mediahub-api
    ```
    The API will be available at `http://localhost:8000` (or the host IP if not running locally). The `-v` flag ensures downloaded/converted files persist outside the container and can be accessed.

## API Endpoints

*(Note: API Key requirement and Rate Limiting depend on `.env` settings `REQUIRE_API_KEY` and `ENABLE_RATE_LIMITING`)*

### Info

*   **`GET /`**
    *   **Description:** Root endpoint for basic API information.
    *   **Response:** JSON object with a welcome message, version, and docs URL.

*   **`GET /status`**
    *   **Description:** Get current system status and statistics (download counts, queue utilization, disk usage).
    *   **Response:** `SystemStatus` JSON object.

*   **`GET /info`**
    *   **Description:** Extract metadata (title, formats, duration, etc.) for a video from a given URL without downloading.
    *   **Query Parameter:** `url` (string, required) - The URL of the video.
    *   **Response:** `VideoInfo` JSON object.

### Downloads

*   **`POST /download`**
    *   **Description:** Start a new download task for a given URL. Allows specifying format ID or stream selection mode.
    *   **Request Body:** `DownloadRequest` JSON object (`url`, `format_id` (optional), `stream_selection_mode` (optional)).
    *   **Response:** `DownloadInfo` JSON object representing the queued task.

*   **`POST /youtube`**
    *   **Description:** Simplified endpoint specifically for YouTube downloads using quality presets.
    *   **Request Body:** JSON object with `url` (string, required), `quality` (string, optional, e.g., "best", "1080p", "720p", "audio"), `mode` (string, optional, "video+audio", "video-only", "audio-only").
    *   **Response:** `DownloadInfo` JSON object representing the queued task.

*   **`GET /status/{download_id}`**
    *   **Description:** Get the current status and progress of a specific download task.
    *   **Path Parameter:** `download_id` (string) - The ID of the download task.
    *   **Response:** `DownloadInfo` JSON object.

*   **`GET /download/{download_id}`** (Also accessible via `GET /{download_id}`)
    *   **Description:** Download the completed file for a specific download task. Only works if the status is `COMPLETED`.
    *   **Path Parameter:** `download_id` (string) - The ID of the download task.
    *   **Response:** `FileResponse` - The actual downloaded file.

*   **`GET /downloads`**
    *   **Description:** List all tracked download tasks and their current status.
    *   **Response:** `List[DownloadInfo]` JSON array.

*   **`DELETE /download/{download_id}`** (Also accessible via `DELETE /{download_id}`)
    *   **Description:** Delete a download task record and attempt to remove the associated file from the temporary directory.
    *   **Path Parameter:** `download_id` (string) - The ID of the download task.
    *   **Response:** `204 No Content`.

### Conversion (Prefix: `/conversion`)

*   **`GET /formats`**
    *   **Description:** Get a list of all supported output formats for conversion, categorized by type (image, video, audio, document).
    *   **Response:** `AvailableFormats` JSON object.

*   **`POST /convert`**
    *   **Description:** Start a new file conversion task. Requires either a `source_url` or a `download_id` (from a previous download or upload).
    *   **Request Body:** `ConversionRequest` JSON object (`source_url` or `download_id`, `output_format`, optional conversion parameters like `width`, `height`, `quality`, etc.).
    *   **Response:** `ConversionInfo` JSON object representing the queued task.

*   **`GET /convert/{conversion_id}`**
    *   **Description:** Get the current status and progress of a specific conversion task.
    *   **Path Parameter:** `conversion_id` (string) - The ID of the conversion task.
    *   **Response:** `ConversionInfo` JSON object.

*   **`GET /download-conversion/{conversion_id}`**
    *   **Description:** Download the completed file for a specific conversion task. Only works if the status is `COMPLETED`.
    *   **Path Parameter:** `conversion_id` (string) - The ID of the conversion task.
    *   **Response:** `FileResponse` - The actual converted file.

*   **`GET /conversions`**
    *   **Description:** List all tracked conversion tasks and their current status.
    *   **Response:** `List[ConversionInfo]` JSON array.

*   **`DELETE /convert/{conversion_id}`**
    *   **Description:** Delete a conversion task record and attempt to remove the associated output file from the temporary directory.
    *   **Path Parameter:** `conversion_id` (string) - The ID of the conversion task.
    *   **Response:** `204 No Content`.

### Uploads (Prefix: `/uploads`)

*   **`POST /upload`**
    *   **Description:** Upload a file to the server. The uploaded file is treated like a completed download task, providing a `download_id` that can be used for conversion.
    *   **Form Data:** `file` (File, required), `title` (string, optional).
    *   **Response:** `DownloadInfo` JSON object representing the uploaded file as a completed download.

*   **`GET /mime-types`**
    *   **Description:** Get a dictionary of common file extensions and their associated MIME types.
    *   **Response:** JSON object containing a `mime_types` dictionary.