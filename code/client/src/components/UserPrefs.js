import React, { useState, useEffect } from 'react';
import axios from 'axios';

const UserPrefs = () => {
  const [colorTheme, setColorTheme] = useState('light');
  const [notifications, setNotifications] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch preferences from API when component mounts
  useEffect(() => {
    const fetchPrefs = async () => {
      try {
        const response = await axios.get('/api/userprefs');  // Replace with your API endpoint
        setColorTheme(response.data.colorTheme);
        setNotifications(response.data.notifications);
      } catch (error) {
        console.error('Could not fetch user preferences:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPrefs();
  }, []);

  // Update preferences in the API when they change
  const updatePrefs = async () => {
    try {
      await axios.post('/api/userprefs', {  // Replace with your API endpoint
        colorTheme,
        notifications
      });
    } catch (error) {
      console.error('Could not update user preferences:', error);
    }
  };

  const handleThemeChange = (e) => {
    setColorTheme(e.target.value);
    updatePrefs();
  };

  const handleNotificationChange = (e) => {
    setNotifications(e.target.checked);
    updatePrefs();
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>User Preferences</h2>
      <div>
        <label>Color Theme:</label>
        <select value={colorTheme} onChange={handleThemeChange}>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </div>
      <div>
        <label>
          Enable Notifications:
          <input type="checkbox" checked={notifications} onChange={handleNotificationChange} />
        </label>
      </div>
    </div>
  );
};

export default UserPrefs;
