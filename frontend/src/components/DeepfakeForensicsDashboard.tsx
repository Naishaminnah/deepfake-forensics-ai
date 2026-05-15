import React, { ReactElement, useState, useEffect } from "react";
import {
  FileImage,
  FileAudio,
  FileVideo,
  Shield,
  LogOut,
  FolderOpen,
  PlusCircle,
} from "lucide-react";

import {
  uploadImage,
  uploadAudio,
  uploadVideo,
  uploadGANFingerprint,
  uploadBigGANReconstruct,
  uploadAndRegisterEvidence,
  createCase as createCaseAPI,
  getCases,
} from "../services/api";

import { useAuth } from "../auth/AuthContext";


type ActiveBox =
  | "image"
  | "audio"
  | "video"
  | "ganfp"
  | "gan_reconstruct_biggan"
  | null;

interface BoxState {
  file: File | null;
  preview: string | null;
  result: any;
}

const DeepfakeForensicsDashboard: React.FC = () => {
  const { logout } = useAuth();
  

  const [activeTab, setActiveTab] = useState<string>("fake_detection");
  const [activeBox, setActiveBox] = useState<ActiveBox>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [enteredCase, setEnteredCase] = useState(false);

  const [showCreateCase, setShowCreateCase] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [newCaseDesc, setNewCaseDesc] = useState("");
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [caseSearch, setCaseSearch] = useState("");
  const [showCaseResults, setShowCaseResults] = useState(false);


  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  


  const [uploadStatus, setUploadStatus] = useState<{
  type: "error" | "success" | "warning";
  message: string;
} | null>(null);
const fileInputRef = React.useRef<HTMLInputElement | null>(null);
const [selectedEvidenceType, setSelectedEvidenceType] =
  useState<"image" | "audio" | "video">("image");

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

  

  const [boxes, setBoxes] = useState<Record<Exclude<ActiveBox, null>, BoxState>>({
    image: { file: null, preview: null, result: null },
    audio: { file: null, preview: null, result: null },
    video: { file: null, preview: null, result: null },
    ganfp: { file: null, preview: null, result: null },
    gan_reconstruct_biggan: { file: null, preview: null, result: null },
  });

  useEffect(() => {
    setUploadStatus(null);
  // Reset all analysis boxes
  setBoxes({
    image: { file: null, preview: null, result: null },
    audio: { file: null, preview: null, result: null },
    video: { file: null, preview: null, result: null },
    ganfp: { file: null, preview: null, result: null },
    gan_reconstruct_biggan: { file: null, preview: null, result: null },
  });

  // Reset blockchain verification
  setVerifyFile(null);
  setVerifyResult(null);
  
  // Collapse active box
  setActiveBox(null);

}, [activeTab]);
 
  useEffect(() => {
  setBoxes({
    image: { file: null, preview: null, result: null },
    audio: { file: null, preview: null, result: null },
    video: { file: null, preview: null, result: null },
    ganfp: { file: null, preview: null, result: null },
    gan_reconstruct_biggan: { file: null, preview: null, result: null },
  });

  setVerifyFile(null);
  setVerifyResult(null);
  setActiveBox(null);

}, [selectedCase]);

  useEffect(() => {
  setUploadStatus(null);
  setVerifyResult(null);
}, [selectedCase]);

  useEffect(() => {
    getCases().then(setCases).catch(console.error);
  }, []);

  useEffect(() => {
    return () => {
      Object.values(boxes).forEach((box) => {
        if (box.preview) URL.revokeObjectURL(box.preview);
      });
    };
  }, [boxes]);

  const filteredCases = cases.filter((c) =>
  `${c.case_id} ${c.title}`.toLowerCase().includes(caseSearch.toLowerCase())
);

  
  const createCase = async () => {
    if (!newCaseTitle.trim()) return alert("Case title required");

    setIsCreatingCase(true);
    try {
      const created = await createCaseAPI({
        title: newCaseTitle,
        description: newCaseDesc,
      });

      setCases((prev) => [created, ...prev]);
      setSelectedCase(created);
      setEnteredCase(true);

      setShowCreateCase(false);
      setNewCaseTitle("");
      setNewCaseDesc("");
    } catch {
      alert("Failed to create case");
    } finally {
      setIsCreatingCase(false);
    }
  };

  const ensureCaseSelected = (): boolean => {
    if (!selectedCase) {
      alert("Please select or enter a case before performing forensic actions.");
      return false;
    }
    return true;
  };

  const handleFileChange = (type: ActiveBox, file?: File) => {
  if (!type || !file) return;

  setUploadStatus(null);

  let expectedType: "image" | "audio" | "video" = "image";

  if (type === "audio") expectedType = "audio";
  if (type === "video") expectedType = "video";

  const error = validateFileType(file, expectedType);

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




  const handleAnalyze = async (type: ActiveBox) => {
    if (!type) return;
    if (!ensureCaseSelected()) return;

    const box = boxes[type];
    if (!box.file) return;

    setIsAnalyzing(true);

    try {
      let result: any;

    const caseDbId = selectedCase.id; // this is the DB primary key
     if (type === "image") {
     result = await uploadImage(box.file, caseDbId);
     }
     else if (type === "audio") {
     result = await uploadAudio(box.file, caseDbId);
     }
     else if (type === "video") {
     result = await uploadVideo(box.file, caseDbId);
     }


      setBoxes((prev) => ({
        ...prev,
        [type]: {
          ...prev[type],
          result,
        },
      }));
    } catch (err) {
      console.error(err);
      alert("Analysis failed. Check backend.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderResult = (result: any) => {
  if (!result || !result.prediction) return null;

  let label = "";
  let confidence = 0;

  // --------------------------
  // IMAGE
  // --------------------------
  if (result.prediction.prediction && result.prediction.confidence !== undefined) {
    label = result.prediction.prediction;
    confidence = Math.round(result.prediction.confidence * 100);
  }
  // --------------------------
  // AUDIO
  // --------------------------
  else if (result.prediction.label && (result.prediction.fake_confidence !== undefined || result.prediction.real_confidence !== undefined)) {
    label = result.prediction.label;
    if (result.prediction.fake_confidence !== undefined) {
      confidence = result.prediction.fake_confidence; // already in %
    } else {
      confidence = Math.max(
        result.prediction.real_confidence || 0,
        result.prediction.fake_confidence || 0
      );
    }
  }
  // --------------------------
  // VIDEO
  // --------------------------
  else if (result.prediction.fake_probability !== undefined && result.prediction.real_probability !== undefined) {
    label = result.prediction.label;
    confidence =
      label.toLowerCase() === "fake"
        ? Math.round(result.prediction.fake_probability * 100)
        : Math.round(result.prediction.real_probability * 100);
  }

  // --------------------------
  // Determine bar color
  // --------------------------
  const barColor = label.toLowerCase() === "fake" ? "bg-red-500" : "bg-green-500";

  return (
    <div className="mt-4">
      {/* Prediction + bar */}
      <p className="font-semibold text-white mb-1">
        Prediction: <span>{label}</span>
      </p>
      <div className="w-full bg-gray-600 h-4 rounded">
        <div
          className={`${barColor} h-4 rounded`}
          style={{ width: `${confidence}%` }}
        ></div>
      </div>
      <p className="text-sm text-gray-300 mt-1">{confidence}% confidence</p>

      {/* JSON Result display */}
      <div className="mt-4 bg-gray-800 p-2 rounded text-xs text-gray-200 overflow-x-auto">
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </div>
    </div>
  );
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
      className={`bg-slate-700 rounded-lg border ${borderColor} transition-all ${
        isActive ? "col-span-1 md:col-span-3 p-6" : "p-4"
      }`}
    >
      <div
        className="cursor-pointer flex items-center gap-2"
        onClick={() => {
          setUploadStatus(null);
  setActiveBox((prevBox) => {
    if (prevBox && prevBox !== type) {
      setBoxes((prev) => {
        const oldPreview = prev[prevBox]?.preview;
        if (oldPreview) URL.revokeObjectURL(oldPreview);

        return {
          ...prev,
          [prevBox]: { file: null, preview: null, result: null },
        };
      });
    }

    return isActive ? null : type;
  });
}}

      >
        {icon}
        <h3 className="font-semibold">{title}</h3>
      </div>

      {isActive && box && (
        <div className="mt-3">
          {/* File input */}
          <input
            type="file"
            id={fileInputId}
            accept={acceptText.replace(/, /g, ",")}
            className="hidden"
            onChange={(e) => {

  setUploadStatus(null); // ⭐ always clear banner

  if (!e.target.files || e.target.files.length === 0) {
    return; // user cancelled picker
  }

  handleFileChange(type, e.target.files[0]);
}}

          />

          {/* Select button */}
          <button
            onClick={() => {
  setUploadStatus(null);   // ⭐ clear banner when picker opens
  document.getElementById(fileInputId)?.click();
}}

            className="px-4 py-2 rounded bg-blue-600 text-white font-semibold"
          >
            Select File
          </button>

          {/* Analyze button */}
          <button
  onClick={() => {

    if (!selectedCase) {
      setUploadStatus({
        type: "error",
        message: "Please select or enter a case before running forensic analysis."
      });
      return;
    }

    if (!box.file) {
      setUploadStatus({
        type: "error",
        message: "No file selected. Please upload evidence before analysis."
      });
      return;
    }

    if (isAnalyzing) return;

    handleAnalyze(type);
  }}

  className={`ml-2 px-4 py-2 rounded text-white font-semibold
    ${
      !box.file || !selectedCase
        ? "bg-gray-500 cursor-not-allowed"
        : "bg-green-600 hover:bg-green-700"
    }`}
>
  {isAnalyzing ? "Analyzing..." : "Analyze"}
</button>


          {!selectedCase && (
            <p className="text-xs text-red-400 mt-2">
              Please select a case before running analysis
            </p>
          )}

          {/* Preview */}
          {box.preview && (
            <div className="mt-4">
              {type === "video" ? (
                <video
                  src={box.preview}
                  className="w-64 h-64 object-cover rounded-lg"
                  controls
                />
              ) : type === "audio" ? (
                <audio src={box.preview} className="w-full" controls />
              ) : (
                <img
                  src={box.preview}
                  className="w-64 h-64 object-cover rounded-lg"
                />
              )}
            </div>
          )}

          {/* Render result with label and confidence bar */}
          {box.result && renderResult(box.result)}
        </div>
      )}
    </div>
  );
};
 const renderGANResult = (result: any) => {
  if (!result) return null;

  const label = result.type || "UNKNOWN";
  const ganType = result.gan_type || "NULL";
  const confidencePct =
    result.confidence !== undefined
      ? Math.round(result.confidence * 100)
      : 0;

  const isFake = label.toLowerCase() === "fake";

  const barColor = isFake ? "bg-red-500" : "bg-green-500";
  const badgeColor = isFake
    ? "bg-red-600/20 text-red-400 border-red-500"
    : "bg-green-600/20 text-green-400 border-green-500";

  return (
    <div className="mt-6 p-5 bg-slate-900 border border-slate-600 rounded-xl shadow-lg">
      {/* Header */}
      <div className="flex flex-wrap gap-3 items-center mb-4">
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold border ${badgeColor}`}
        >
          {label}
        </span>

        <span className="px-3 py-1 rounded-full text-sm font-semibold bg-blue-600/20 text-blue-300 border border-blue-500">
          GAN: {ganType}
        </span>

        {result.ledger_status && (
          <span className="px-3 py-1 rounded-full text-xs bg-slate-700 text-slate-300 border border-slate-500">
            {result.ledger_status}
          </span>
        )}
      </div>

      {/* Confidence */}
      <div className="mb-2">
        <p className="text-sm text-slate-300 mb-1">
          Confidence: <span className="font-semibold">{confidencePct}%</span>
        </p>
        <div className="w-full bg-gray-700 h-4 rounded">
          <div
            className={`${barColor} h-4 rounded transition-all`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>

    </div>
  );
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
        {uploadStatus.type === "warning" && "⚖ Evidence Notice"}
        {uploadStatus.type === "success" && "✔ Operation Successful"}
      </p>

      <p className="text-sm mt-1">{uploadStatus.message}</p>
    </div>
  );
};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white p-6">
      {/* HEADER */}
      <div className="max-w-7xl mx-auto mb-8 flex justify-between items-center">
        <div className="flex gap-3 items-center">
          <Shield className="w-10 h-10 text-blue-400" />
          <div>
            <h1 className="text-3xl font-bold">AI Digital Forensics Platform</h1>
            <p className="text-blue-300 text-sm">
              Deepfake Detection & Evidence Authentication
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-600/40 bg-slate-800 text-emerald-300 hover:bg-emerald-600/10"
        >
          <LogOut size={16} /> Logout
        </button>
      </div>

      {/* CASE WORKSPACE */}
      {!enteredCase && (
        <div className="max-w-xl mx-auto mt-20 bg-slate-800 border border-slate-700 rounded-2xl p-8 shadow-xl text-center">
          <FolderOpen className="mx-auto w-12 h-12 text-blue-400 mb-4" />
          <h2 className="text-2xl font-bold mb-2">Case Workspace</h2>
          <p className="text-slate-300 mb-6">
            Select or create a case to begin forensic analysis
          </p>

          <div className="text-left mb-6 relative">
  <label className="block text-sm font-semibold text-blue-300 mb-2">
    Select Existing Case
  </label>

  <input
    type="text"
    placeholder="Search by case ID or title…"
    value={caseSearch}
    onChange={(e) => {
      setCaseSearch(e.target.value);
      setShowCaseResults(true);
    }}
    onFocus={() => setShowCaseResults(true)}
    className="w-full p-3 rounded-lg bg-slate-700 border border-blue-500/50 
               focus:outline-none focus:ring-2 focus:ring-blue-500
               placeholder:text-slate-400"
  />

  {/* Dropdown */}
  {showCaseResults && caseSearch && (
    <div className="absolute z-20 w-full mt-2 bg-slate-800 
                    border border-slate-600 rounded-lg shadow-xl 
                    max-h-60 overflow-y-auto">
      {filteredCases.length === 0 && (
        <p className="p-3 text-sm text-slate-400">
          No matching cases
        </p>
      )}

      {filteredCases.map((c) => (
        <div
          key={c.id}
          onClick={() => {
            setSelectedCase(c);
            setCaseSearch(`${c.case_id} — ${c.title}`);
            setShowCaseResults(false);
          }}
          className="px-4 py-3 cursor-pointer hover:bg-blue-600/20 
                     border-b border-slate-700 last:border-none"
        >
          <p className="text-white font-semibold">{c.case_id}</p>
          <p className="text-xs text-slate-400">{c.title}</p>
        </div>
      ))}
    </div>
  )}
</div>


          <button
            disabled={!selectedCase}
            onClick={() => {setEnteredCase(true);
              setShowCreateCase(false);
            }}
            
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold mb-3"
          >
            Enter Case
          </button>

          <button
            onClick={() => setShowCreateCase(true)}
            className="w-full py-3 rounded-lg border border-blue-500 text-blue-300 hover:bg-blue-500/10 flex items-center justify-center gap-2"
          >
            <PlusCircle size={18} /> Create New Case
          </button>
        </div>
      )}

      {enteredCase && selectedCase && (
        <>
        {activeTab !== "blockchain" && renderUploadStatusBanner()}

          <div className="max-w-7xl mx-auto mb-6 bg-blue-900/40 border border-blue-500 rounded-lg px-5 py-4">
            <p className="text-xs uppercase tracking-wide text-blue-300">
              Active Case
            </p>
            <h3 className="text-xl font-semibold">{selectedCase.case_id}</h3>
            <p className="text-blue-200">{selectedCase.title}</p>
          </div>

          <div className="max-w-7xl mx-auto mb-6 flex gap-2 bg-slate-800 p-2 rounded-lg">
            {[
              { id: "fake_detection", label: "Deepfake Detection" },
              { id: "gan_fp", label: "GAN Fingerprinter" },
              { id: "gan_reconstruct", label: "GAN Reconstruction" },
              { id: "blockchain", label: "Blockchain Verification" },
             ].map((tab) => (
    <button
      key={tab.id}
      onClick={() => setActiveTab(tab.id)}
      className={`flex-1 py-3 rounded-lg ${
        activeTab === tab.id
          ? "bg-blue-600 text-white"
          : "bg-slate-700 text-slate-300"
      }`}
    >
      {tab.label}
    </button>
))}

          </div>

          {activeTab === "fake_detection" && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-7xl mx-auto">
              {renderBox(
                "image",
                "Image Analysis",
                "image/jpeg, image/png",
                <FileImage className="w-8 h-8 text-blue-400 mb-2" />,
                "border-blue-500"
              )}
              {renderBox(
                "audio",
                "Audio Analysis",
                "audio/wav, audio/mp3, audio/m4a",
                <FileAudio className="w-8 h-8 text-green-400 mb-2" />,
                "border-green-500"
              )}
              {renderBox(
                "video",
                "Video Analysis",
                "video/mp4, video/avi, video/mov",
                <FileVideo className="w-8 h-8 text-purple-400 mb-2" />,
                "border-purple-500"
              )}
            </div>
          )}
          {activeTab === "gan_fp" && (
  <div className="max-w-5xl mx-auto mt-10 p-8 bg-slate-800 border border-slate-700 rounded-2xl shadow-xl">
    <h2 className="text-2xl font-bold mb-4 text-blue-400">
      GAN Fingerprinting Module
    </h2>

    <p className="text-slate-300 mb-6 text-lg leading-relaxed">
      Upload a suspicious image to detect{" "}
      <span className="text-blue-400 font-semibold">
        which GAN model generated it
      </span>.
      Our system analyzes artifact patterns, frequency signatures, and texture
      distortions to identify the exact generative model 
      (StyleGAN, ProGAN, BigGAN, Glide, StableDiffusion, etc).
    </p>

    <div className="flex flex-col md:flex-row gap-8 items-center">

      {/* Upload Box */}
      <div className="bg-slate-700 border border-blue-500 rounded-xl p-6 w-full md:w-1/2">
        <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <FileImage className="w-6 h-6 text-blue-400" />
          Upload Image
        </h3>

        <input
          type="file"
          id="gan-fp-input"
          accept="image/png, image/jpeg"
          className="hidden"
          onChange={(e) => {

  setUploadStatus(null);

  if (!e.target.files || e.target.files.length === 0) {
    return; // picker cancelled
  }

  const file = e.target.files[0];

  const error = validateFileType(file, "image");

  if (error) {
    setUploadStatus({ type: "error", message: error });
    return;
  }

  setBoxes(prev => ({
    ...prev,
    ganfp: {
      file,
      preview: (() => {
        if (prev.ganfp.preview) {
          URL.revokeObjectURL(prev.ganfp.preview);
        }
        return URL.createObjectURL(file);
      })(),
      result: null
    }
  }));
}}

        />

        <button
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold"
          onClick={() => {
  setUploadStatus(null);
  document.getElementById("gan-fp-input")?.click();
}}

        >
          Choose Image
        </button>

        {boxes.ganfp?.preview && (
          <img
            src={boxes.ganfp.preview}
            className="w-64 h-64 object-cover rounded-lg mt-4 shadow-lg"
          />
        )}

        <button
          className="mt-4 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold w-full"
          disabled={!boxes.ganfp?.file || isAnalyzing || !selectedCase}
          onClick={async () => {
            if (!ensureCaseSelected()) return;
            if (!boxes.ganfp?.file) return;

            setIsAnalyzing(true);


            try {
              const result = await uploadGANFingerprint(
                boxes.ganfp.file,
                selectedCase.id
              );

              // Force new object reference to trigger re-render
              setBoxes(prev => ({
                ...prev,
                ganfp: {
                  ...prev.ganfp,
                  result: { ...result, _uniqueId: Date.now() + Math.random() },
                },
              }));
            } catch (err) {
              console.error(err);
              alert("GAN fingerprinting failed. Check backend logs.");
              setBoxes(prev => ({
                ...prev,
                ganfp: { ...prev.ganfp, result: null },
              }));
            } finally {
              setIsAnalyzing(false);
            }
          }}
        >
          {isAnalyzing ? "Analyzing..." : "Detect GAN Source"}
        </button>
      </div>

      {/* Description Box */}
      <div className="md:w-1/2 bg-slate-700 p-6 rounded-xl border border-slate-600 shadow-lg">
        <h3 className="text-xl font-bold text-blue-300 mb-3">How It Works</h3>
        <ul className="text-slate-300 space-y-2 text-sm leading-relaxed">
          <li>• Analyzes GAN-specific frequency fingerprints</li>
          <li>• Detects convolution skip-connection artifacts</li>
          <li>• Identifies model families (ADM, VQDM, BigGAN, Glide, etc.)</li>
          <li>• Provides confidence estimate for reports</li>
        </ul>
      </div>
    </div>

    {/* JSON Results */}
   {boxes.ganfp?.result && (
  <div key={boxes.ganfp.result._uniqueId}>
    {/* Visual GAN result */}
    {renderGANResult(boxes.ganfp.result)}

    {/* Collapsible JSON output */}
    <details className="mt-4 bg-slate-800 border border-gray-600 rounded-lg">
      <summary className="cursor-pointer px-4 py-2 text-sm text-blue-300 hover:text-blue-200 font-semibold select-none">
        View JSON Output
      </summary>

      <div className="p-4 text-xs text-slate-300 overflow-x-auto">
        <pre>{JSON.stringify(boxes.ganfp.result, null, 2)}</pre>
      </div>
    </details>
  </div>
)}


  </div>
)}



      {activeTab === "gan_reconstruct" && (
  <div className="max-w-5xl mx-auto mt-10 p-8 bg-slate-800 border border-slate-700 rounded-2xl shadow-xl">
    <h2 className="text-2xl font-bold mb-6 text-blue-400 text-center">
      GAN Latent Reconstruction Module
    </h2>

    <p className="text-slate-300 mb-8 text-lg leading-relaxed text-center">
      Reconstruct the most probable original image from a deepfake. <br />
      <span className="text-blue-400 font-semibold">
        Note: This is a complex task; reconstruction may not exceed ~95% accuracy.
      </span>
    </p>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* BigGAN Reconstruction Box */}
      <div className="bg-slate-700 border border-blue-500 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-3">BigGAN Reconstruction</h3>
        <p className="text-slate-300 mb-4 text-sm">
          For general images (non-human faces). Upload an image to reconstruct its likely original form.
        </p>

        <input
          type="file"
          id="biggan-input"
          accept="image/png, image/jpeg"
          className="hidden"
          onChange={(e) => {

  setUploadStatus(null);

  if (!e.target.files || e.target.files.length === 0) {
    return;
  }

  const file = e.target.files[0];

  const error = validateFileType(file, "image");

  if (error) {
    setUploadStatus({ type: "error", message: error });
    return;
  }

  setBoxes(prev => ({
    ...prev,
    gan_reconstruct_biggan: {
      file,
      preview: (() => {
        if (prev.gan_reconstruct_biggan.preview) {
          URL.revokeObjectURL(prev.gan_reconstruct_biggan.preview);
        }
        return URL.createObjectURL(file);
      })(),
      result: null
    }
  }));
}}

        />

        <button
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold w-full"
          onClick={() => {
  setUploadStatus(null);
  document.getElementById("biggan-input")?.click();
}}

        >
          Choose Image
        </button>

        {boxes.gan_reconstruct_biggan?.preview && (
          <img
            src={boxes.gan_reconstruct_biggan.preview}
            className="w-full h-64 object-cover rounded-lg mt-4 shadow-lg"
          />
        )}

        <button
          className="mt-4 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold w-full"
          disabled={!boxes.gan_reconstruct_biggan?.file || isAnalyzing || !selectedCase}
          onClick={async () => {
             if (!ensureCaseSelected()) return;
             if (!boxes.gan_reconstruct_biggan?.file) return;
             setIsAnalyzing(true);


            try {
              const result = await uploadBigGANReconstruct(
                boxes.gan_reconstruct_biggan.file,
                selectedCase.id
              );
              setBoxes((prev) => ({
                ...prev,
                gan_reconstruct_biggan: { ...prev.gan_reconstruct_biggan, result },
              }));
            } catch (err) {
              console.error(err);
              alert("BigGAN reconstruction failed. Check backend logs.");
            } finally {
              setIsAnalyzing(false);
            }
          }}
        >
          {isAnalyzing ? "Reconstructing..." : "Start Reconstruction"}
        </button>

        {boxes.gan_reconstruct_biggan?.result && (
              <img
                   src={boxes.gan_reconstruct_biggan.result}
                   className="w-full h-64 object-cover rounded-lg mt-4 shadow-lg"
                   alt="BigGAN Reconstructed"
               />
       )}

      </div>

      
    </div>
  </div>
)}


      {activeTab === "blockchain" && (
  <div className="max-w-4xl mx-auto mt-10 p-8 bg-slate-800 border border-slate-700 rounded-2xl shadow-xl">

    <h2 className="text-2xl font-bold text-blue-400 mb-4">
      Blockchain Evidence Registration
    </h2>

    <p className="text-slate-300 mb-6">
      Upload forensic evidence to IPFS and anchor its cryptographic hash
      on the blockchain. This creates a <b>court-admissible record</b>.
    </p>

    {/* Evidence type */}
   <div className="mb-5">
  <label className="block text-sm font-semibold text-blue-300 mb-2">
    Evidence Type
  </label>

  <div className="relative">
    <select
      value={selectedEvidenceType}
      onChange={(e) => {

        const val = e.target.value as "image" | "audio" | "video";

        setSelectedEvidenceType(val);
        setUploadStatus(null);
        setVerifyResult(null);
        setVerifyFile(null);
        if (fileInputRef.current) {
  fileInputRef.current.value = "";
}
      }}
      className="
        w-full appearance-none
        bg-slate-700
        border border-blue-500/40
        rounded-xl
        px-4 py-3 pr-10
        text-white font-semibold
        shadow-lg
        focus:outline-none
        focus:ring-2 focus:ring-blue-500
        hover:border-blue-400
        transition-all
      "
    >
      <option value="image">📷 Image Evidence</option>
      <option value="video">🎬 Video Evidence</option>
      <option value="audio">🎧 Audio Evidence</option>
    </select>

    {/* Custom arrow */}
    <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-blue-300">
      ▼
    </div>
  </div>
</div>


    {/* File upload */}
    <input
    ref={fileInputRef}
  type="file"
  className="w-full mb-4"
  onClick={() => {
    setUploadStatus(null);     // ⭐ Clear message when picker opens
    setVerifyResult(null);
  }}
  onChange={(e) => {

    if (!e.target.files || e.target.files.length === 0) {
      return;
    }

    const file = e.target.files[0];

    const error = validateFileType(file, selectedEvidenceType);

    if (error) {
      setUploadStatus({
        type: "error",
        message: `Selected evidence type is ${selectedEvidenceType.toUpperCase()}, but uploaded file does not match.`,
      });
      return;
    }

    setVerifyFile(file);
  }}
/>


    {uploadStatus && (
  <div
    className={`mt-5 p-4 rounded-xl border shadow-lg transition-all
      ${
        uploadStatus.type === "error"
          ? "bg-red-900/40 border-red-500 text-red-300"
          : uploadStatus.type === "warning"
          ? "bg-yellow-900/40 border-yellow-500 text-yellow-300"
          : "bg-emerald-900/40 border-emerald-500 text-emerald-300"
      }`}
  >
    <p className="font-semibold">
      {uploadStatus.type === "error" && "⚠ Upload Error"}
      {uploadStatus.type === "warning" && "⚖ Evidence Already Registered"}
      {uploadStatus.type === "success" && "✔ Upload Successful"}
    </p>

    <p className="text-sm mt-1">{uploadStatus.message}</p>
  </div>
)}

    <button
      className="w-full px-4 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold"
      disabled={!verifyFile || isVerifying || !selectedCase}
      onClick={async () => {
          if (!ensureCaseSelected()) return;
          if (!verifyFile) return;
          setIsVerifying(true);
          setVerifyResult(null);
          setUploadStatus(null);

        try {
          const result = await uploadAndRegisterEvidence(
            verifyFile,
            selectedCase.id
          );
          setVerifyResult(result);
        } catch (e: any) {

  if (e?.response?.status === 409) {
    setUploadStatus({
      type: "warning",
      message: "Evidence already exists in this case. Blockchain proof has already been established.",
    });
    return;
  }

  setUploadStatus({
    type: "error",
    message: "Evidence upload failed. Please try again or contact system administrator.",
  });
}

finally {
          setIsVerifying(false);
        }
      }}
    >
      {isVerifying ? "Registering on Blockchain..." : "Upload & Register"}
    </button>

    {verifyResult && (
  <div className="mt-6 p-6 bg-slate-900 border border-slate-600 rounded-xl shadow-lg">
    <h3 className="text-xl font-bold mb-4 text-blue-400">
      Blockchain Registration Result
    </h3>

    {/* Status badge */}
    <div className="mb-4">
      <span className="px-3 py-1 rounded-full text-sm font-semibold 
        bg-emerald-600/20 text-emerald-300 border border-emerald-500">
        {verifyResult.status}
      </span>
    </div>

    {/* Key-value grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-300">
      <div>
        <p className="text-slate-400">Evidence Type</p>
        <p className="font-semibold text-white uppercase">
          {verifyResult.evidence_type}
        </p>
      </div>

      <div>
        <p className="text-slate-400">Timestamp</p>
        <p className="font-mono text-white">
          {new Date(verifyResult.timestamp * 1000).toLocaleString()}
        </p>
      </div>

      <div className="md:col-span-2">
        <p className="text-slate-400">Evidence Hash (SHA-256)</p>
        <p className="font-mono break-all text-white">
          {verifyResult.evidence_hash}
        </p>
      </div>

      <div className="md:col-span-2">
        <p className="text-slate-400">Metadata Hash</p>
        <p className="font-mono break-all text-white">
          {verifyResult.metadata_hash}
        </p>
      </div>

      <div className="md:col-span-2">
        <p className="text-slate-400">IPFS CID</p>
        <p className="font-mono break-all text-blue-300">
          {verifyResult.ipfs_cid}
        </p>
      </div>

      <div className="md:col-span-2">
        <p className="text-slate-400">Registered By (Wallet)</p>
        <p className="font-mono break-all text-white">
          {verifyResult.registered_by}
        </p>
      </div>

      <div className="md:col-span-2">
        <p className="text-slate-400">Transaction Hash</p>
        <p className="font-mono break-all text-purple-300">
          {verifyResult.tx_hash}
        </p>
      </div>
    </div>

    {/* Collapsible JSON */}
    <details className="mt-6 bg-slate-800 border border-slate-600 rounded-lg">
      <summary className="cursor-pointer px-4 py-2 text-sm text-blue-300 font-semibold">
        View Full Blockchain JSON
      </summary>
      <pre className="p-4 text-xs text-slate-300 overflow-x-auto">
        {JSON.stringify(verifyResult, null, 2)}
      </pre>
    </details>
  </div>
)}

  </div>
)}


        </>
      )}
      
    {showCreateCase && (
  <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div className="bg-slate-800 w-full max-w-md rounded-xl p-6 border border-slate-600 shadow-2xl">
      <h2 className="text-xl font-bold text-blue-400 mb-4">
        Create New Case
      </h2>

      <label className="block text-sm text-slate-300 mb-1">
        Case Title *
      </label>
      <input
        className="w-full mb-3 p-2 rounded bg-slate-700 border border-slate-600"
        value={newCaseTitle}
        onChange={(e) => setNewCaseTitle(e.target.value)}
        placeholder="e.g. Deepfake Extortion Case"
      />

      <label className="block text-sm text-slate-300 mb-1">
        Description (optional)
      </label>
      <textarea
        className="w-full mb-4 p-2 rounded bg-slate-700 border border-slate-600"
        rows={3}
        value={newCaseDesc}
        onChange={(e) => setNewCaseDesc(e.target.value)}
        placeholder="Short summary of the case"
      />

      <div className="flex justify-end gap-3">
        <button
          onClick={() => setShowCreateCase(false)}
          className="px-4 py-2 rounded bg-slate-600 hover:bg-slate-500"
        >
          Cancel
        </button>

        <button
          onClick={createCase}
          disabled={isCreatingCase}
          className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 font-semibold"
        >
          {isCreatingCase ? "Creating..." : "Create Case"}
        </button>
      </div>
    </div>
  </div>
)}

    </div>
  );
};

export default DeepfakeForensicsDashboard;