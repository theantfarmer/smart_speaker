import React, { useState, useEffect, useRef } from 'react';
import ChatHistory from './ChatHistory';
import InputArea from './InputArea';
import '../../styles/Chat.css';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [chatHistoryHeight, setChatHistoryHeight] = useState(null);
  const resizeHandleRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    const initializeChat = async () => {
      await setupSSE();
      sendAjaxRequest('/', {}, function() {
        console.log("Initial AJAX request completed");
      });
    };
  
    initializeChat();
  
    return () => {
      // Any cleanup code (e.g., closing SSE connection) can go here
    };
  }, []);
  

  const sendAjaxRequest = (endpoint, data, successCallback) => {
    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(successCallback)
    .catch(error => console.error('Error:', error));
  };
  
  const setupSSE = () => {
    console.log("Setting up SSE connection");
    return new Promise((resolve) => {
      const source = new EventSource("/stream");
      
      source.onopen = (event) => {
        console.log("SSE connection opened", event);
        resolve();
      };
      
      source.onerror = (error) => {
        console.error("SSE connection error:", error);
        resolve(); // Resolve even on error to prevent blocking
      };
      
      source.onmessage = (event) => {
        console.log("Received SSE message:", event.data);
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'messages_update' && Array.isArray(data.data.messages)) {
            setMessages(data.data.messages);
          }
        } catch (error) {
          console.error("Error parsing SSE message:", error);
        }
      };
    });
  };

  const handleScrollToTop = async () => {
    try {
      await fetch('/scrolled_to_top', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Error handling scroll to top:', error);
    }
  };

  const sendQuery = async (input) => {
    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ input }),
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
    } catch (error) {
      console.error('Error sending query:', error);
    }
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (resizeHandleRef.current && resizeHandleRef.current.dataset.resizing === 'true') {
        const containerRect = chatContainerRef.current.getBoundingClientRect();
        const newChatHeight = e.clientY - containerRect.top;
        setChatHistoryHeight(Math.max(100, Math.min(newChatHeight, containerRect.height - 100)));
      }
    };

    const handleMouseUp = () => {
      if (resizeHandleRef.current) {
        resizeHandleRef.current.dataset.resizing = 'false';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleResizeStart = (e) => {
    e.preventDefault();
    if (resizeHandleRef.current) {
      resizeHandleRef.current.dataset.resizing = 'true';
    }
  };

  return (
    <div className="chat-interface-container" ref={chatContainerRef}>
      <ChatHistory 
        messages={messages} 
        onScrollToTop={handleScrollToTop}
        style={chatHistoryHeight !== null ? { height: `${chatHistoryHeight}px`, minHeight: 'unset' } : undefined}
      />
      <div 
        className="resize-handle"
        ref={resizeHandleRef}
        onMouseDown={handleResizeStart}
      />
      <InputArea 
        onSendMessage={sendQuery}
        style={chatHistoryHeight !== null ? { height: `calc(100% - ${chatHistoryHeight}px - 15px)` } : undefined}
      />
    </div>
  );
}

export default Chat;