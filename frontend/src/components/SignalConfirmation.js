import React, { useState } from 'react';
import './SignalConfirmation.css';

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
    <div className="signal-confirmation-container">
      <h3>Signal Prediction</h3>
      {refereeCropImageUrl && (
        <div className="referee-crop-display">
          <h4>Referee Crop:</h4>
          <img src={refereeCropImageUrl} alt="Referee Crop" />
        </div>
      )}
      <p className="signal-prediction-info">Predicted: <b>{predictedClass}</b> (Confidence: {(confidence * 100).toFixed(1)}%)</p>
      <div className="signal-feedback-options">
        <label>
          <input
            type="radio"
            checked={isCorrect}
            onChange={() => setIsCorrect(true)}
          />
          Correct
        </label>
        <label>
          <input
            type="radio"
            checked={!isCorrect}
            onChange={() => setIsCorrect(false)}
          />
          Incorrect
        </label>
      </div>
      {!isCorrect && (
        <div className="signal-correct-class-selection">
          <label>Select correct class:&nbsp;</label>
          <select value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
            {SIGNAL_CLASSES.map(cls => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        </div>
      )}
      <button onClick={handleSubmit}>Submit</button>
    </div>
  );
};

export default SignalConfirmation; 