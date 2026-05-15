//frontend/src/components/UserDeepfakeDashboard.tsx
import React, { ReactElement, useState, useEffect } from "react";
import {
  FileImage,
  FileAudio,
  FileVideo,
  Shield,
  LogOut,
} from "lucide-react";

import {
  uploadUserImage,
  uploadUserAudio,
  uploadUserVideo,
} from "../services/api";

import { useAuth } from "../auth/AuthContext";

type ActiveBox = "image" | "audio" | "video" | null;

interface BoxState {
  file: File | null;
  preview: string | null;
  result: any;
}

const UserDeepfakeDashboard: React.FC = () => {
  const { logout } = useAuth();

  const [activeBox, setActiveBox] = useState<ActiveBox>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
  type: "error" | "success" | "warning";
  message: string;
} | null>(null);

  const [boxes, setBoxes] = useState<Record<Exclude<ActiveBox, null>, BoxState>>({
    image: { file: null, preview: null, result: null },
    audio: { file: null, preview: null, result: null },
    video: { file: null, preview: null, result: null },
  });

  useEffect(() => {
    return () => {
      Object.values(boxes).forEach((box) => {
        if (box.preview) URL.revokeObjectURL(box.preview);
      });
    };
  }, [boxes]);
  const FILE_TYPE_RULES: Record<string, string[]> = {
  image: ["image/png", "image/jpeg", "image/jpg"],
  audio: ["audio/wav", "audio/mp3", "audio/mpeg", "audio/flac", "audio/m4a"],
  video: ["video/mp4", "video/avi", "video/quicktime", "video/mov"],
};

const validateFileType = (
  file?: File,
  expectedType?: "image" | "audio" | "video"
): string | null => {

  if (!file) return "No file selected.";

  if (!file.type || file.type === "") {
    return "Unable to verify file type. File may be corrupted or renamed.";
  }

  if (!expectedType) return null;

  const allowed = FILE_TYPE_RULES[expectedType];

  if (!allowed.includes(file.type)) {
    return `Unsupported file format. Please upload a valid ${expectedType.toUpperCase()} file.`;
  }

  return null;
};

  const handleFileChange = (type: ActiveBox, file?: File) => {
  if (!type || !file) return;

  setUploadStatus(null); // ⭐ clear banner

  const error = validateFileType(file, type);

  if (error) {
    setUploadStatus({
      type: "error",
      message: error,
    });
    return;
  }

  setBoxes((prev) => ({
    ...prev,
    [type]: {
      file,
      preview: (() => {
        const oldPreview = prev[type]?.preview;
        if (oldPreview) URL.revokeObjectURL(oldPreview);
        return URL.createObjectURL(file);
      })(),
      result: null,
    },
  }));
};
  const renderUploadStatusBanner = () => {
  if (!uploadStatus) return null;

  return (
    <div
      className={`max-w-7xl mx-auto mb-6 p-4 rounded-xl border shadow-lg transition-all
        ${
          uploadStatus.type === "error"
            ? "bg-red-900/40 border-red-500 text-red-300"
            : uploadStatus.type === "warning"
            ? "bg-yellow-900/40 border-yellow-500 text-yellow-300"
            : "bg-emerald-900/40 border-emerald-500 text-emerald-300"
        }`}
    >
      <p className="font-semibold">
        {uploadStatus.type === "error" && "⚠ File Validation Failed"}
        {uploadStatus.type === "warning" && "⚖ Notice"}
        {uploadStatus.type === "success" && "✔ Success"}
      </p>

      <p className="text-sm mt-1">{uploadStatus.message}</p>
    </div>
  );
};

  const handleAnalyze = async (type: ActiveBox) => {
    if (!type) return;
    const box = boxes[type];
    if (!box.file) return;

    setIsAnalyzing(true);

    try {
      let result: any;

      if (type === "image") result = await uploadUserImage(box.file);
      else if (type === "audio") result = await uploadUserAudio(box.file);
      else if (type === "video") result = await uploadUserVideo(box.file);

      setBoxes((prev) => ({
        ...prev,
        [type]: {
          ...prev[type],
          result,
        },
      }));
    } catch (err) {
      console.error(err);
      setUploadStatus({
  type: "error",
  message: "Analysis failed. Please try again."
});

    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderResult = (result: any) => {
    if (!result) return null;

    let label = "";
    let confidence = 0;

    if (
      typeof result.prediction === "string" &&
      typeof result.confidence === "number"
    ) {
      label = result.prediction;
      confidence = Math.round(result.confidence * 100);
    } else if (
      result.label &&
      (result.fake_confidence !== undefined ||
        result.real_confidence !== undefined)
    ) {
      label = result.label;
      confidence =
        result.label.toLowerCase() === "fake"
          ? Math.round(result.fake_confidence ?? 0)
          : Math.round(result.real_confidence ?? 0);
    } else if (
      result.prediction?.prediction &&
      result.prediction?.confidence !== undefined
    ) {
      label = result.prediction.prediction;
      confidence = Math.round(result.prediction.confidence * 100);
    } else if (
      result.prediction?.label &&
      (result.prediction.fake_confidence !== undefined ||
        result.prediction.real_confidence !== undefined)
    ) {
      label = result.prediction.label;
      confidence =
        label.toLowerCase() === "fake"
          ? Math.round(result.prediction.fake_confidence ?? 0)
          : Math.round(result.prediction.real_confidence ?? 0);
    } else if (
      result.prediction?.fake_probability !== undefined &&
      result.prediction?.real_probability !== undefined
    ) {
      label = result.prediction.label;
      confidence =
        label.toLowerCase() === "fake"
          ? Math.round(result.prediction.fake_probability * 100)
          : Math.round(result.prediction.real_probability * 100);
    } else {
      return (
        <div className="mt-4 text-red-400 text-sm">
          ⚠️ Unsupported result format
        </div>
      );
    }

    const barColor =
      label.toLowerCase() === "fake"
        ? "bg-gradient-to-r from-red-600 to-red-400"
        : "bg-gradient-to-r from-emerald-500 to-green-400";

    return (
      <div className="mt-6 p-5 rounded-2xl bg-slate-900/70 backdrop-blur border border-slate-600 shadow-lg">
        <p className="font-semibold mb-3 text-lg">
          Prediction:{" "}
          <span
            className={
              label.toLowerCase() === "fake"
                ? "text-red-400"
                : "text-green-400"
            }
          >
            {label}
          </span>
        </p>

        <div className="w-full bg-slate-700/70 h-4 rounded-full overflow-hidden shadow-inner">
          <div
            className={`${barColor} h-4 rounded-full transition-all duration-700`}
            style={{ width: `${confidence}%` }}
          />
        </div>

        <p className="text-sm text-slate-300 mt-2">
          {confidence}% confidence
        </p>

        <details className="mt-4">
          <summary className="cursor-pointer text-xs text-blue-400 hover:text-blue-300">
            View raw JSON
          </summary>
          <pre className="mt-2 text-xs bg-black/60 p-3 rounded-xl overflow-x-auto border border-slate-700">
            {JSON.stringify(result, null, 2)}
          </pre>
        </details>
      </div>
    );
  };

  const resetBox = (type: Exclude<ActiveBox, null>) => {
  setBoxes((prev) => ({
    ...prev,
    [type]: { file: null, preview: null, result: null },
  }));
};


  const renderBox = (
    type: ActiveBox,
    title: string,
    acceptText: string,
    icon: ReactElement,
    borderColor: string
  ) => {
    const isActive = activeBox === type;
    const box = type ? boxes[type] : null;
    const fileInputId = `input-${type}`;

    return (
      <div
        className={`relative rounded-2xl transition-all duration-500 ${
          isActive
            ? "md:col-span-3 p-6 bg-slate-800/80 backdrop-blur border-2 shadow-2xl"
            : "p-5 bg-slate-800/50 backdrop-blur border hover:bg-slate-700/60 hover:shadow-xl"
        } ${borderColor}`}
      >
        <div
          className="cursor-pointer flex items-center gap-3"
          onClick={() => {
           setUploadStatus(null);
           if (!isActive && activeBox) {
           resetBox(activeBox);
           }
           setActiveBox(isActive ? null : type);
           }}
         >
          <div className="p-2 rounded-xl bg-black/30">{icon}</div>
          <h3 className="font-semibold text-lg tracking-wide">{title}</h3>
        </div>

        {isActive && box && (
          <div className="mt-5">
            <input
  type="file"
  id={fileInputId}
  accept={acceptText.replace(/, /g, ",")}
  className="hidden"
  onChange={(e) => {

  setUploadStatus(null);

  // ⭐ If user cancelled file picker
  if (!e.target.files || e.target.files.length === 0) {

    setBoxes((prev) => ({
      ...prev,
      [type!]: { file: null, preview: null, result: null }
    }));

    return;
  }

  handleFileChange(type, e.target.files[0]);
}}

/>


            <div className="flex gap-3">
              <button
  onClick={() => {

    // ⭐ Clear banner
    setUploadStatus(null);

    // ⭐ Reset preview + result before choosing new file
    setBoxes((prev) => {
      const oldPreview = prev[type!]?.preview;
      if (oldPreview) URL.revokeObjectURL(oldPreview);

      return {
        ...prev,
        [type!]: { file: null, preview: null, result: null }
      };
    });

    document.getElementById(fileInputId)?.click();
  }}

  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold shadow-md transition"
>
  Select File
</button>


              <button
                onClick={() => handleAnalyze(type)}
                disabled={!box.file || isAnalyzing}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-semibold shadow-md transition disabled:opacity-50"
              >
                {isAnalyzing ? "Analyzing..." : "Analyze"}
              </button>
            </div>

            {box.preview && (
              <div className="mt-5">
                {type === "video" ? (
                  <video
                    src={box.preview}
                    controls
                    className="w-72 rounded-xl shadow-lg border border-slate-600"
                  />
                ) : type === "audio" ? (
                  <audio src={box.preview} controls />
                ) : (
                  <img
                    src={box.preview}
                    className="w-72 h-72 object-cover rounded-xl shadow-lg border border-slate-600"
                  />
                )}
              </div>
            )}

            {box.result && renderResult(box.result)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900 via-slate-900 to-black text-white p-8">
      <div className="max-w-7xl mx-auto mb-10 flex justify-between items-center">
        <div className="flex gap-4 items-center">
          <div className="p-3 rounded-2xl bg-blue-600/20 shadow-inner">
            <Shield className="w-10 h-10 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-wide">
              Deepfake Detection Dashboard
            </h1>
            <p className="text-blue-300 text-sm">
              Upload media to detect AI-generated content
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center gap-2 px-5 py-2 rounded-xl border border-emerald-500/40 bg-slate-900/70 text-emerald-300 hover:bg-emerald-600/10 transition"
        >
          <LogOut size={16} /> Logout
        </button>
      </div>
      {renderUploadStatusBanner()}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-7xl mx-auto">
        {renderBox(
          "image",
          "Image Analysis",
          "image/jpeg, image/png",
          <FileImage className="w-8 h-8 text-blue-400" />,
          "border-blue-500/40"
        )}

        {renderBox(
          "audio",
          "Audio Analysis",
          "audio/wav, audio/mp3, audio/m4a",
          <FileAudio className="w-8 h-8 text-emerald-400" />,
          "border-emerald-500/40"
        )}

        {renderBox(
          "video",
          "Video Analysis",
          "video/mp4, video/avi, video/mov",
          <FileVideo className="w-8 h-8 text-purple-400" />,
          "border-purple-500/40"
        )}
      </div>
    </div>
  );
};

export default UserDeepfakeDashboard;
