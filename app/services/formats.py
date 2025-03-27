import os
import mimetypes
from typing import Dict, List, Optional, Set, Tuple

mimetypes.init()

IMAGE_FORMATS = {
    "png": {"mime": "image/png", "transparent": True},
    "jpg": {"mime": "image/jpeg", "transparent": False},
    "jpeg": {"mime": "image/jpeg", "transparent": False},
    "webp": {"mime": "image/webp", "transparent": True},
    "gif": {"mime": "image/gif", "transparent": True},
    "bmp": {"mime": "image/bmp", "transparent": False},
    "tiff": {"mime": "image/tiff", "transparent": True},
    "ico": {"mime": "image/x-icon", "transparent": True},
    "svg": {"mime": "image/svg+xml", "transparent": True},
}

VIDEO_FORMATS = {
    "mp4": {"mime": "video/mp4", "container": "mp4", "codecs": ["h264", "aac"]},
    "webm": {"mime": "video/webm", "container": "webm", "codecs": ["vp9", "opus"]},
    "mkv": {
        "mime": "video/x-matroska",
        "container": "matroska",
        "codecs": ["h264", "aac"],
    },
    "avi": {"mime": "video/x-msvideo", "container": "avi", "codecs": ["h264", "mp3"]},
    "mov": {"mime": "video/quicktime", "container": "mov", "codecs": ["h264", "aac"]},
    "flv": {"mime": "video/x-flv", "container": "flv", "codecs": ["h264", "aac"]},
    "gif": {"mime": "image/gif", "container": "gif", "codecs": [None, None]},
}

AUDIO_FORMATS = {
    "mp3": {"mime": "audio/mpeg", "codec": "mp3"},
    "wav": {"mime": "audio/wav", "codec": "pcm_s16le"},
    "ogg": {"mime": "audio/ogg", "codec": "vorbis"},
    "aac": {"mime": "audio/aac", "codec": "aac"},
    "flac": {"mime": "audio/flac", "codec": "flac"},
    "m4a": {"mime": "audio/m4a", "codec": "aac"},
}

DOCUMENT_FORMATS = {
    "pdf": {"mime": "application/pdf"},
    "txt": {"mime": "text/plain"},
    "md": {"mime": "text/markdown"},
    "html": {"mime": "text/html"},
}

ALL_FORMATS = {**IMAGE_FORMATS, **VIDEO_FORMATS, **AUDIO_FORMATS, **DOCUMENT_FORMATS}


def get_media_type(file_path: str) -> Optional[str]:
    """
    Determine the media type of a file based on its extension
    Returns: One of "image", "video", "audio", "document", or None
    """
    if not os.path.exists(file_path):
        return None
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext in IMAGE_FORMATS:
        return "image"
    elif ext in VIDEO_FORMATS:
        return "video"
    elif ext in AUDIO_FORMATS:
        return "audio"
    elif ext in DOCUMENT_FORMATS:
        return "document"
    return None


def get_mime_type(format_ext: str) -> Optional[str]:
    """
    Get the MIME type for a given format extension
    """
    if format_ext in ALL_FORMATS:
        return ALL_FORMATS[format_ext].get("mime")
    return None


def supports_transparency(format_ext: str) -> bool:
    """
    Check if the format supports transparency
    """
    if format_ext in IMAGE_FORMATS:
        return IMAGE_FORMATS[format_ext].get("transparent", False)
    return False


def get_conversion_command(
    source_path: str, output_path: str, options: Dict
) -> List[str]:
    """
    Generate the appropriate conversion command based on input and output formats
    Args:
        source_path: Path to source file
        output_path: Path for output file
        options: Dictionary of conversion options
    Returns:
        Command list for subprocess execution
    """
    source_ext = os.path.splitext(source_path)[1].lower().lstrip(".")
    output_ext = os.path.splitext(output_path)[1].lower().lstrip(".")
    source_type = get_media_type(source_path)
    if source_type == "image":
        return get_image_conversion_command(source_path, output_path, options)
    elif source_type == "video":
        return get_video_conversion_command(source_path, output_path, options)
    elif source_type == "audio":
        return get_audio_conversion_command(source_path, output_path, options)
    return ["ffmpeg", "-i", source_path, output_path]


def get_image_conversion_command(
    source_path: str, output_path: str, options: Dict
) -> List[str]:
    """
    Generate ImageMagick command for image conversion
    """
    command = ["convert", source_path]

    if options.get("width") or options.get("height"):
        width = options.get("width", "")
        height = options.get("height", "")
        resize_mode = options.get("resize_mode", "fit")
        if resize_mode == "fit":
            command.extend(["-resize", f"{width}x{height}"])
        elif resize_mode == "fill":
            command.extend(
                [
                    "-resize",
                    f"{width}x{height}^",
                    "-gravity",
                    "center",
                    "-extent",
                    f"{width}x{height}",
                ]
            )
        elif resize_mode == "stretch":
            command.extend(["-resize", f"{width}x{height}!"])

    if options.get("quality"):
        command.extend(["-quality", str(options.get("quality"))])

    # Fix the alpha handling to be compatible with older ImageMagick versions
    if options.get("preserve_transparency", True):
        output_ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        if supports_transparency(output_ext):
            # Older versions of ImageMagick don't support -alpha on
            # Just skip this part, as transparency is preserved by default
            pass
        else:
            # For formats that don't support transparency
            command.extend(["-background", "white", "-flatten"])

    command.append(output_path)
    return command


def get_video_conversion_command(
    source_path: str, output_path: str, options: Dict
) -> List[str]:
    """
    Generate FFmpeg command for video conversion
    """
    command = ["ffmpeg", "-i", source_path]
    if options.get("video_codec"):
        command.extend(["-c:v", options.get("video_codec")])
    if options.get("audio_codec"):
        command.extend(["-c:a", options.get("audio_codec")])
    if options.get("video_bitrate"):
        command.extend(["-b:v", options.get("video_bitrate")])
    if options.get("audio_bitrate"):
        command.extend(["-b:a", options.get("audio_bitrate")])
    if options.get("fps"):
        command.extend(["-r", str(options.get("fps"))])
    if options.get("width") and options.get("height"):
        command.extend(["-vf", f"scale={options.get('width')}:{options.get('height')}"])
    if options.get("start_time") is not None:
        command.extend(["-ss", str(options.get("start_time"))])
    if options.get("end_time") is not None:
        command.extend(["-to", str(options.get("end_time"))])
    command.extend(["-y", output_path])
    return command


def get_audio_conversion_command(
    source_path: str, output_path: str, options: Dict
) -> List[str]:
    """
    Generate FFmpeg command for audio conversion
    """
    command = ["ffmpeg", "-i", source_path]
    if options.get("audio_codec"):
        command.extend(["-c:a", options.get("audio_codec")])
    else:
        output_ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        if output_ext in AUDIO_FORMATS and AUDIO_FORMATS[output_ext].get("codec"):
            command.extend(["-c:a", AUDIO_FORMATS[output_ext]["codec"]])
    if options.get("audio_bitrate"):
        command.extend(["-b:a", options.get("audio_bitrate")])
    if options.get("start_time") is not None:
        command.extend(["-ss", str(options.get("start_time"))])
    if options.get("end_time") is not None:
        command.extend(["-to", str(options.get("end_time"))])
    command.extend(["-y", output_path])
    return command


def can_convert(source_type: str, source_ext: str, target_ext: str) -> bool:
    """
    Check if conversion between formats is supported
    """
    if source_ext == target_ext:
        return True
    if source_type == "image" and target_ext in IMAGE_FORMATS:
        return True
    elif source_type == "video" and target_ext in VIDEO_FORMATS:
        return True
    elif source_type == "audio" and target_ext in AUDIO_FORMATS:
        return True
    if source_type == "video" and target_ext in AUDIO_FORMATS:
        return True
    if source_type == "video" and target_ext == "gif":
        return True
    return False
