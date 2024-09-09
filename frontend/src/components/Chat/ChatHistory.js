import React, { useState, useEffect, useRef } from 'react';
import MessageItem from './MessageItem';

function ChatHistory({ messages, onScrollToTop }) {
  const [displayMessages, setDisplayMessages] = useState([]);
  const [distanceFromBottom, setDistanceFromBottom] = useState(0);
  const chatContainerRef = useRef(null);
  const isAtBottomRef = useRef(true);

  useEffect(() => {
    if (Array.isArray(messages) && messages.length > 0) {
      const validMessages = messages.filter(msg => 
        msg && typeof msg === 'object' && 'content' in msg && 'role' in msg
      );
      isAtBottomRef.current = isScrolledToBottom();
      setDisplayMessages(validMessages);
    }
  }, [messages]);
  
  useEffect(() => {
    if (isAtBottomRef.current) {
      scrollToBottom();
    } else {
      restoreScrollPosition();
    }
  }, [displayMessages]);

  useEffect(() => {
    const chatContainer = chatContainerRef.current;
    if (chatContainer) {
      const handleScroll = () => {
        const container = chatContainerRef.current;
        if (container.scrollTop === 0) {
          const currentDistanceFromBottom = container.scrollHeight - container.clientHeight;
          setDistanceFromBottom(currentDistanceFromBottom);
          onScrollToTop();
        }
      };

      chatContainer.addEventListener('scroll', handleScroll);
      return () => chatContainer.removeEventListener('scroll', handleScroll);
    }
  }, [onScrollToTop]);

  const isScrolledToBottom = () => {
    const container = chatContainerRef.current;
    if (container) {
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      const threshold = 1; // To account for potential floating point inaccuracies
      return distanceFromBottom <= threshold;
    }
    return false;
  };

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  const restoreScrollPosition = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight - chatContainerRef.current.clientHeight - distanceFromBottom;
    }
  };

  return (
    <div 
      className="chat-history-box" 
      ref={chatContainerRef}
    >
      {displayMessages.map((message, index) => (
        <MessageItem 
          key={message.database_id || index}
          message={message}
        />
      ))}
    </div>
  );
}

export default ChatHistory;