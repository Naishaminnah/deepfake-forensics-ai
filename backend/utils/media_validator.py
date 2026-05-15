from fastapi import HTTPException

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/flac", "audio/mp4"}


def validate_media(file, expected: str):
    if not file.content_type:
        raise HTTPException(400, "Unable to detect file type")

    if expected == "image" and file.content_type not in IMAGE_TYPES:
        raise HTTPException(
            400,
            "Unsupported image format. Allowed formats: JPG, PNG, WEBP."
        )

    if expected == "video" and file.content_type not in VIDEO_TYPES:
        raise HTTPException(
            400,
            "Unsupported video format. Allowed formats: MP4, MOV, AVI, MKV."
        )

    if expected == "audio" and file.content_type not in AUDIO_TYPES:
        raise HTTPException(
            400,
            "Unsupported audio format. Allowed formats: WAV, MP3, FLAC, M4A."
        )
