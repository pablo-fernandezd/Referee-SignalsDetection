import React, { useState } from 'react';

const SIGNAL_CLASSES = [
  'armLeft', 'armRight', 'hits', 'leftServe', 'net', 'outside', 'rightServe', 'touched', 'none'
];

const SignalConfirmation = ({ predictedClass, confidence, signalBbox, cropFilenameForSignal, onConfirm }) => {
  const [isCorrect, setIsCorrect] = useState(true);
  const [selectedClass, setSelectedClass] = useState(predictedClass || 'none');

  const handleSubmit = () => {
    onConfirm({
      correct: isCorrect,
      selected_class: isCorrect ? predictedClass : selectedClass,
      signal_bbox_yolo: signalBbox
    });
  };

  // Construct the URL for the referee crop image
  const refereeCropImageUrl = cropFilenameForSignal ? `http://localhost:5000/api/referee_crop_image/${cropFilenameForSignal}` : null;

  return (
    <div>
      <h3>Signal Prediction</h3>
      {refereeCropImageUrl && (
        <div style={{ marginBottom: 20 }}>
          <h4>Referee Crop:</h4>
          <img src={refereeCropImageUrl} alt="Referee Crop" style={{ maxWidth: '100%', height: 'auto' }} />
        </div>
      )}
      <p>Predicted: <b>{predictedClass}</b> (Confidence: {(confidence * 100).toFixed(1)}%)</p>
      <div>
        <label>
          <input
            type="radio"
            checked={isCorrect}
            onChange={() => setIsCorrect(true)}
          />
          Correct
        </label>
        <label style={{ marginLeft: 20 }}>
          <input
            type="radio"
            checked={!isCorrect}
            onChange={() => setIsCorrect(false)}
          />
          Incorrect
        </label>
      </div>
      {!isCorrect && (
        <div style={{ marginTop: 10 }}>
          <label>Select correct class:&nbsp;</label>
          <select value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
            {SIGNAL_CLASSES.map(cls => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        </div>
      )}
      <button onClick={handleSubmit} style={{ marginTop: 15 }}>Submit</button>
    </div>
  );
};

export default SignalConfirmation; 