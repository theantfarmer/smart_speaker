import React from 'react';

function MessageItem({ message }) {
  const { role, content, function_request } = message;

  const formatMessage = () => {
    let formattedContent = content;
    let agentPrefix = 'Agent';
    
    switch (role) {
      case 'User':
        return <><b>User: </b>{formattedContent}<br /></>;
      case 'Agent':
        if (function_request) {
          agentPrefix = function_request
            .replace(/^(speak_to_|chat_with_llm_|get_)/, '')
            .replace('_status', '')
            .replace(/_/g, ' ')
            .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
        }
        return <><b>{agentPrefix}: </b>{formattedContent}<br /></>;
      case 'tool':
        let toolContent = function_request ? 
          `(${function_request}: ${formattedContent})` : 
          formattedContent;
        return <div style={{ textAlign: 'center' }}><i>{toolContent}</i></div>;
      case 'system':
        let systemContent = function_request ? 
          `(${function_request}: ${formattedContent})` : 
          formattedContent;
        return <><b>System: </b>{systemContent}<br /></>;
      default:
        return <><b>{role}:</b> {formattedContent}<br /></>;
    }
  };

  return (
    <div className={`message ${role.toLowerCase()}`}>
      {formatMessage()}
    </div>
  );
}

export default MessageItem;