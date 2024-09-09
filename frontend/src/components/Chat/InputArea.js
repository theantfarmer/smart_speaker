import React, { useState, useEffect } from 'react';

function InputArea({ onSendMessage, style }) {
  const [userInput, setUserInput] = useState('');
  const [selectedAssistant, setSelectedAssistant] = useState('hey claude');
  const [selectedAttachment, setSelectedAttachment] = useState('attachments');

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        const botSettings = settings.preferences.default_bot;
        setSelectedAssistant(botSettings.default);
      } catch (error) {
        console.error('Error fetching settings:', error);
      }
    };

    fetchSettings();
  }, []);

  const handleSend = () => {
    if (userInput.trim()) {
      onSendMessage(`${selectedAssistant} ${userInput}`);
      setUserInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="input-area" style={style}>
      <div className="menu-container">
        <select 
          id="attachment-select"
          value={selectedAttachment} 
          onChange={(e) => setSelectedAttachment(e.target.value)}
        >
          <option value="attachments">Attach Stuff</option>
          <option value="select">Select from files</option>
          <option value="upload">Upload</option>
          <option value="manage">Go to File Manager</option>
        </select>
        <select 
          id="assistant-select"
          value={selectedAssistant} 
          onChange={(e) => setSelectedAssistant(e.target.value)}
        >
          <option value="hey karen">Karen</option>
          <option value="hey home assistant">Home Assistant</option>
          <option value="hey claude">Claude</option>
          <option value="hey opus">Claude (Opus)</option>
          <option value="hey chatgpt">ChatGPT</option>
        </select>
      </div>
      <div className="input-row">
        <textarea 
          id="user-input"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Query the machine"
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
}

export default InputArea;