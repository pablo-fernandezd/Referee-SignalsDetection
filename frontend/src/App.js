import React, { useState } from 'react';
import UploadForm from './components/UploadForm';
import CropConfirmation from './components/CropConfirmation';
import ManualCrop from './components/ManualCrop';
import SignalConfirmation from './components/SignalConfirmation';

function App() {
  const [step, setStep] = useState(0);
  const [uploadData, setUploadData] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [cropUrl, setCropUrl] = useState(null);
  const [cropFilename, setCropFilename] = useState(null);
  const [originalFilename, setOriginalFilename] = useState(null);
  const [signalResult, setSignalResult] = useState(null);
  const [cropFilenameForSignal, setCropFilenameForSignal] = useState(null);

  // Step 0: Upload
  const handleUpload = (data, file) => {
    setUploadData(data);
    setImageFile(file);
    setOriginalFilename(data.filename);

    if (data.crop_url) {
      setCropUrl('http://localhost:5000' + data.crop_url);
      setCropFilename(data.crop_url.split('/').pop());
      setStep(1);
    } else if (data.error && data.filename) {
      alert(data.error + ". Please manually crop.");
      setStep(3);
    }
  };

  // Step 1: Crop confirmation
  const handleCropConfirm = async (confirmed) => {
    if (confirmed) {
      const res = await fetch('http://localhost:5000/api/confirm_crop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          original_filename: originalFilename, 
          crop_filename: cropFilename,
          bbox: uploadData.bbox
        })
      });
      const data = await res.json();

      if (data.status === 'ok' && data.crop_filename_for_signal) {
        setCropFilenameForSignal(data.crop_filename_for_signal);
        // Process signal
        const signalRes = await fetch('http://localhost:5000/api/process_signal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ crop_filename_for_signal: data.crop_filename_for_signal })
        });
        const signalResultData = await signalRes.json();
        setSignalResult(signalResultData);
        setStep(2);
      }
    } else {
      setStep(3); // Go to manual crop
    }
  };

  // Step 2: Signal confirmation
  const handleSignalConfirm = async ({ correct, selected_class }) => {
    await fetch('http://localhost:5000/api/confirm_signal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        crop_filename_for_signal: cropFilenameForSignal,
        correct,
        selected_class,
        signal_bbox_yolo: signalResult ? signalResult.bbox_xywhn : null
      })
    });
    alert('Thank you for your feedback!');
    window.location.reload();
  };

  // Step 3: Manual crop
  const handleManualCrop = async ({ bbox, class_id }) => {
    const res = await fetch('http://localhost:5000/api/manual_crop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: originalFilename, bbox, class_id })
    });
    const data = await res.json();

    if (data.status === 'ok' && data.crop_filename_for_signal) {
      setCropFilenameForSignal(data.crop_filename_for_signal);
      // After manual crop, proceed to signal detection
      const signalRes = await fetch('http://localhost:5000/api/process_signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ crop_filename_for_signal: data.crop_filename_for_signal })
      });
      const signalResultData = await signalRes.json();
      setSignalResult(signalResultData);
      setStep(2); // Go to signal confirmation
    } else {
      alert('Error saving manual crop or no class selected.');
      window.location.reload();
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 20 }}>
      <h2>Referee & Signal Detection</h2>
      {step === 0 && <UploadForm onUpload={handleUpload} />}
      {step === 1 && cropUrl && (
        <CropConfirmation cropUrl={cropUrl} onConfirm={handleCropConfirm} />
      )}
      {step === 2 && signalResult && (
        <SignalConfirmation
          predictedClass={signalResult.predicted_class}
          confidence={signalResult.confidence}
          signalBbox={signalResult.bbox_xywhn}
          cropFilenameForSignal={cropFilenameForSignal}
          onConfirm={handleSignalConfirm}
        />
      )}
      {step === 3 && imageFile && (
        <ManualCrop imageFile={imageFile} onSubmit={handleManualCrop} />
      )}
    </div>
  );
}

export default App;
