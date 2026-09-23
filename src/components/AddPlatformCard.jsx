import React from 'react';
import { Plus } from 'lucide-react';

export default function AddPlatformCard({ onClick }) {
  return (
    <button
      className="add-platform-card"
      onClick={onClick}
      type="button"
      aria-label="Add financial platform or account"
    >
      <div className="add-icon-circle">
        <Plus size={20} strokeWidth={2} />
      </div>
      <div className="add-card-label">Add platform</div>
    </button>
  );
}
