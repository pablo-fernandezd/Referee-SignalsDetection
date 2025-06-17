import React from 'react';
import './CropConfirmation.css';

const CropConfirmation = ({ cropUrl, onConfirm }) => {
  return (
    <div className="crop-confirmation-container">
      <h3>Is the referee crop correct?</h3>
      <img src={cropUrl} alt="Referee Crop" />
      <div className="crop-confirmation-buttons">
        <button onClick={() => onConfirm(true)}>Yes</button>
        <button onClick={() => onConfirm(false)}>No</button>
      </div>
    </div>
  );
};

export default CropConfirmation; 