import React from 'react';
import { BrowserRouter as Router, Route } from 'react-router-dom';
import Menu from './Menu';
import ChatHistory from './ChatHistory';
import UserPrefs from './UserPrefs';
import Secrets from './Secrets';

function App() {
  return (
    <>
         <div>
              <img src="/horsy.jpg" alt="Description of the image" style={{ width: '300px', height: 'auto' }} />


        </div>
      <Router>
        <Menu />
        <Route path="/chathistory" component={ChatHistory} />
        <Route path="/userprefs" component={UserPrefs} />
        <Route path="/secrets" component={Secrets} />
      </Router>
    </>
  );
}

export default App;
