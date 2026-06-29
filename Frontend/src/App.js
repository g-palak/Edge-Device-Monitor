import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  const [telemetryData, setTelemetryData] = useState({});
  const [devices, setDevices] = useState(['device-001', 'device-002', 'device-003']);
  const [selectedDevice, setSelectedDevice] = useState('device-001');
  const [configValue, setConfigValue] = useState('');
  const [configs, setConfigs] = useState({});
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);

  // Connect to WebSocket
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    const ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'telemetry') {
        setTelemetryData(prev => {
          const deviceData = prev[data.device_id] || [];
          const newData = [...deviceData, {
            time: new Date(data.ts).toLocaleTimeString(),
            metric: data.metric,
            timestamp: data.ts
          }].slice(-20); // Keep last 20 points
          
          return {
            ...prev,
            [data.device_id]: newData
          };
        });
      } else if (data.type === 'config_update') {
        updateConfigStatus(data);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      setWsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    wsRef.current = ws;
  };

  const updateConfigStatus = (configUpdate) => {
    setConfigs(prev => {
      const deviceConfigs = prev[configUpdate.device_id] || [];
      const updatedConfigs = deviceConfigs.map(config => 
        config.id === configUpdate.config_id 
          ? { ...config, status: configUpdate.status, applied_at: configUpdate.applied_at }
          : config
      );
      
      return {
        ...prev,
        [configUpdate.device_id]: updatedConfigs
      };
    });
  };

  const pushConfig = async () => {
    if (!configValue.trim()) return;
    
    try {
      const configData = JSON.parse(configValue);
      const response = await fetch(`${API_URL}/devices/${selectedDevice}/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config_data: configData }),
      });
      
      if (response.ok) {
        const newConfig = await response.json();
        setConfigs(prev => ({
          ...prev,
          [selectedDevice]: [...(prev[selectedDevice] || []), newConfig]
        }));
        setConfigValue('');
      }
    } catch (error) {
      console.error('Failed to push config:', error);
      alert('Invalid JSON or failed to push config');
    }
  };

  const loadConfigs = async (deviceId) => {
    try {
      const response = await fetch(`${API_URL}/devices/${deviceId}/configs`);
      if (response.ok) {
        const configData = await response.json();
        setConfigs(prev => ({
          ...prev,
          [deviceId]: configData
        }));
      }
    } catch (error) {
      console.error('Failed to load configs:', error);
    }
  };

  useEffect(() => {
    loadConfigs(selectedDevice);
  }, [selectedDevice]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return '#ffd700';
      case 'applied': return '#4caf50';
      case 'failed': return '#f44336';
      default: return '#999';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Edge Device Dashboard</h1>
        <div className={`connection-status ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? '🟢 Live' : '🔴 Disconnected'}
        </div>
      </header>

      <div className="dashboard">
        <div className="device-selector">
          <h2>Devices</h2>
          <div className="device-buttons">
            {devices.map(device => (
              <button
                key={device}
                className={`device-btn ${selectedDevice === device ? 'active' : ''}`}
                onClick={() => setSelectedDevice(device)}
              >
                {device}
                {telemetryData[device] && (
                  <span className="metric-badge">
                    {telemetryData[device][telemetryData[device].length - 1]?.metric.toFixed(1)}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="telemetry-panel">
          <h2>Live Telemetry - {selectedDevice}</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={telemetryData[selectedDevice] || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis domain={['auto', 'auto']} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="metric"
                  stroke="#8884d8"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="config-panel">
            <h3>Push Configuration</h3>
            <div className="config-form">
              <textarea
                value={configValue}
                onChange={(e) => setConfigValue(e.target.value)}
                placeholder='{"sample_rate": 5, "threshold": 75.0}'
                rows={4}
              />
              <button onClick={pushConfig}>Push Config to {selectedDevice}</button>
            </div>

            <div className="configs-list">
              <h4>Configuration History</h4>
              {configs[selectedDevice]?.map(config => (
                <div key={config.id} className="config-item">
                  <div className="config-header">
                    <span>Config #{config.id}</span>
                    <span style={{ color: getStatusColor(config.status) }}>
                      ● {config.status}
                    </span>
                  </div>
                  <div className="config-details">
                    <pre>{JSON.stringify(JSON.parse(config.config_data), null, 2)}</pre>
                  </div>
                  <div className="config-timestamps">
                    <small>Created: {new Date(config.created_at).toLocaleString()}</small>
                    {config.applied_at && (
                      <small>Applied: {new Date(config.applied_at).toLocaleString()}</small>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;