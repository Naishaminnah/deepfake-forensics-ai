export const IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
];

export const VIDEO_TYPES = [
  "video/mp4",
  "video/quicktime",
  "video/x-msvideo",
  "video/x-matroska",
];

export const AUDIO_TYPES = [
  "audio/wav",
  "audio/mpeg",
  "audio/flac",
  "audio/mp4",
];

export function validateMediaFile(
  file: File,
  expected: "image" | "video" | "audio"
): { valid: boolean; message?: string } {
  if (!file.type) {
    return {
      valid: false,
      message: "Unable to determine file format.",
    };
  }

  const map = {
    image: IMAGE_TYPES,
    video: VIDEO_TYPES,
    audio: AUDIO_TYPES,
  };

  if (!map[expected].includes(file.type)) {
    const readable = {
      image: "JPG, PNG, WEBP",
      video: "MP4, MOV, AVI, MKV",
      audio: "WAV, MP3, FLAC, M4A",
    };

    return {
      valid: false,
      message: `Unsupported ${expected} format. Allowed formats: ${readable[expected]}.`,
    };
  }

  return { valid: true };
}
