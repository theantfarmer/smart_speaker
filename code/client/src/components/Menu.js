import React from 'react';
import { Link } from 'react-router-dom';

function Menu() {
  return (
    <div>
      <ul>
        <li><Link to="/chathistory">Chat History</Link></li> {/* Add this line */}
        <li><Link to="/userprefs">User Preferences</Link></li>
        <li><Link to="/secrets">Secrets</Link></li>
      </ul>
    </div>
  );
}

export default Menu;