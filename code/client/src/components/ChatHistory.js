import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5555/api';

function ChatHistory() {
  const [chatHistory, setChatHistory] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const scrollRef = useRef(null);
  
  const fetchChatHistory = () => {
    setIsLoading(true);
    axios.get(`${API_BASE_URL}/chat-history`)
      .then(response => {
        setChatHistory(response.data);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('There was an error fetching data:', error);
        setError(error);
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchChatHistory();  // Initial fetch
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      const { scrollHeight } = scrollRef.current;
      scrollRef.current.scrollTop = scrollHeight;
    }
  }, [chatHistory]);
  
  
  const sendMessage = () => {
    // Send message to server
    axios.post(`${API_BASE_URL}/send-message`, { message: newMessage })
    .then(response => {
      fetchChatHistory();  // Fetch updated chat history
      setNewMessage('');  // Clear the input field
    })
    .catch(error => {
      console.error('Error sending message:', error);
    });
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div>
      <h2>Chat History</h2>
      <ul ref={scrollRef} style={{ overflowY: 'auto', height: '400px' }}>
        {chatHistory.map((chat, index) => (
          <li key={index}>
            {chat[1]}: {chat[2]}
          </li>
        ))}
      </ul>
      <input
        type="text"
        value={newMessage}
        onChange={e => setNewMessage(e.target.value)}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}

export default ChatHistory;
