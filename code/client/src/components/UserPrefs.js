import React, { useState, useEffect } from 'react';
import axios from 'axios';

const UserPrefs = () => {
  const [customInstructions, setCustomInstructions] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    axios.get("http://localhost:5555/api/get-custom-instructions")
      .then(response => {
        setCustomInstructions(response.data.instructions);
        setIsLoading(false);
      })
      .catch(error => {
        console.log("Error fetching custom instructions: ", error);
        setIsLoading(false);
      });
  }, []);

  const handleCustomInstructionsChange = (e) => {
    const newInstructions = e.target.value;
    setCustomInstructions(newInstructions);
  };

  const handleUpdateButtonClick = () => {
    axios.post("http://localhost:5555/api/update-custom-instructions", { instructions: customInstructions })
      .then(response => {
        console.log("Successfully updated instructions: ", response.data);
      })
      .catch(error => {
        console.log("Error updating custom instructions: ", error);
      });
  };

  if (isLoading) {
    return <div>send money</div>;
  }

  return (
    <div>
      <h2>User Preferences</h2>
      <div>
        <label>
          <b>Custom Instructions  </b>
          for the chatbot
          <textarea 
            value={customInstructions} 
            onChange={handleCustomInstructionsChange}
            rows="10" // Set the number of rows
            cols="60" // Set the number of columns
          ></textarea>
        </label>
      </div>
      <div>
        <button onClick={handleUpdateButtonClick}>Update</button>
      </div>
    </div>
  );
};

export default UserPrefs;
