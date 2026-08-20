export function AdminAttributionBanner() {
  return (
    <aside className="admin-attribution-banner" role="note" aria-label="Administrator attribution notice">
      <span className="admin-attribution-icon" aria-hidden="true">◆</span>
      <div>
        <strong>Administrator access is attributed</strong>
        <span>You are viewing another employee’s incident. Your access and every saved change are attributed to your administrator account.</span>
      </div>
    </aside>
  );
}
