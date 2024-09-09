import React from 'react';
import Chat from './components/Chat/Chat';
import './styles/App.css';

function App() {
  return (
    <div className="App">
      <div className="header">
        <h1>Robotic Psychotic</h1>
      </div>
      <nav>
        <a href="/homepage">Home</a>
        <a href="/">Chat</a>
        <a href="/settings">Settings</a>
      </nav>
      <div className="content">
        <Chat />
      </div>
    </div>
  );
}

export default App;