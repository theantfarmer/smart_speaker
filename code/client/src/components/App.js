import React from 'react';
import { BrowserRouter as Router, Route } from 'react-router-dom';
import Menu from './Menu';
import ChatHistory from './ChatHistory'; // Import ChatHistory
import UserPrefs from './UserPrefs';
import Secrets from './Secrets';

function App() {
  return (
    <Router>
      <Menu />
      <Route path="/chathistory" component={ChatHistory} /> {/* Add this line */}
      <Route path="/userprefs" component={UserPrefs} />
      <Route path="/secrets" component={Secrets} />
    </Router>
  );
}

export default App;
