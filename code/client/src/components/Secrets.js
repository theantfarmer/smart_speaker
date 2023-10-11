import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Secrets = () => {
  const [apiKeyGPT, setApiKeyGPT] = useState('');
  const [apiKeyOther, setApiKeyOther] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Fetch existing API keys from the server when the component mounts
  useEffect(() => {
    const fetchKeys = async () => {
      try {
        const response = await axios.get('/api/apikeys'); // Replace with your API endpoint
        setApiKeyGPT(response.data.apiKeyGPT);
        setApiKeyOther(response.data.apiKeyOther);
      } catch (error) {
        console.error('Could not fetch API keys:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchKeys();
  }, []);

  // Update API keys on the server
  const updateKeys = async () => {
    try {
      await axios.post('/api/apikeys', { // Replace with your API endpoint
        apiKeyGPT,
        apiKeyOther,
      });
    } catch (error) {
      console.error('Could not update API keys:', error);
    }
  };

  const handleGPTKeyChange = (e) => {
    setApiKeyGPT(e.target.value);
    updateKeys();
  };

  const handleOtherKeyChange = (e) => {
    setApiKeyOther(e.target.value);
    updateKeys();
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>API Key Preferences</h2>
      <div>
        <label>GPT API Key:</label>
        <input type="password" value={apiKeyGPT} onChange={handleGPTKeyChange} />
      </div>
      <div>
        <label>Other Service API Key:</label>
        <input type="password" value={apiKeyOther} onChange={handleOtherKeyChange} />
      </div>
    </div>
  );
};

export default Secrets;
