import React from 'react';

const CropConfirmation = ({ cropUrl, onConfirm }) => {
  return (
    <div>
      <h3>Is the referee crop correct?</h3>
      <img src={cropUrl} alt="Referee Crop" style={{ maxWidth: '300px', border: '2px solid #333' }} />
      <div style={{ marginTop: 10 }}>
        <button onClick={() => onConfirm(true)}>Yes</button>
        <button onClick={() => onConfirm(false)}>No</button>
      </div>
    </div>
  );
};

export default CropConfirmation; 