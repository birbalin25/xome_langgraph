import { ChevronDown, Search, User } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import type { UserSummary } from "../../types";

interface UserDropdownProps {
  users: UserSummary[];
  selectedId: string;
  onSelect: (userId: string) => void;
  loading: boolean;
}

export default function UserDropdown({
  users,
  selectedId,
  onSelect,
  loading,
}: UserDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = users.find((u) => u.user_id === selectedId);
  const filtered = users.filter((u) => {
    const q = search.toLowerCase();
    return (
      u.first_name.toLowerCase().includes(q) ||
      u.last_name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q)
    );
  });

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        disabled={loading || users.length === 0}
        className="flex w-full items-center justify-between rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm shadow-sm transition hover:border-xome-400 disabled:opacity-50"
      >
        {loading ? (
          <span className="text-gray-400">Loading users...</span>
        ) : selected ? (
          <span className="flex items-center gap-2">
            <User className="h-4 w-4 text-xome-600" />
            {selected.first_name} {selected.last_name}
            <span className="text-gray-400">
              ({selected.rec_count} recs)
            </span>
          </span>
        ) : (
          <span className="text-gray-400">
            {users.length === 0
              ? "No users found — adjust filters"
              : "Select a user..."}
          </span>
        )}
        <ChevronDown className="h-4 w-4 text-gray-400" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
          <div className="border-b border-gray-100 p-2">
            <div className="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5">
              <Search className="h-4 w-4 text-gray-400" />
              <input
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or email..."
                className="w-full bg-transparent text-sm outline-none"
              />
            </div>
          </div>
          <ul className="max-h-60 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-4 py-2 text-sm text-gray-400">
                No matches
              </li>
            ) : (
              filtered.map((u) => (
                <li key={u.user_id}>
                  <button
                    onClick={() => {
                      onSelect(u.user_id);
                      setOpen(false);
                      setSearch("");
                    }}
                    className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition hover:bg-xome-50 ${
                      u.user_id === selectedId
                        ? "bg-xome-50 font-medium text-xome-700"
                        : ""
                    }`}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-xome-100 text-xs font-bold text-xome-700">
                      {u.first_name[0]}
                      {u.last_name[0]}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">
                        {u.first_name} {u.last_name}
                      </div>
                      <div className="truncate text-xs text-gray-400">
                        {u.email} &middot; {u.preferred_city},{" "}
                        {u.preferred_state} &middot; {u.rec_count} recs
                      </div>
                    </div>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
