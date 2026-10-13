import Logo from './Logo.jsx';

const STATUS_TEXT = {
  connected: 'Connected to bridge',
  connecting: 'Connecting to bridge...',
  idle: 'Not connected - click to reconnect',
  error: 'Bridge unreachable - click to retry',
};

export default function NavBar({ bridgeState, onReconnect, onDashboard, onLogout }) {
  return (
    <header className="navbar">
      <button className="navbar-logo" onClick={onDashboard} aria-label="Go to dashboard"><Logo /></button>
      <nav className="navbar-right">
        <button
          className={'bridge-dot ' + bridgeState}
          onClick={bridgeState === 'connected' ? undefined : onReconnect}
          title={STATUS_TEXT[bridgeState] || bridgeState}
          aria-label={STATUS_TEXT[bridgeState] || bridgeState}
        />
        <button className="nav-link" onClick={onDashboard}>Dashboard</button>
        <button className="logout-button" onClick={onLogout}>LOGOUT</button>
      </nav>
    </header>
  );
}
