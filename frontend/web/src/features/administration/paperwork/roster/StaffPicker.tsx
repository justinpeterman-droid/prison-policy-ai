import { useEffect, useId, useRef, useState } from "react";
import { listAdminStaff, type AdminStaffMember } from "../../api";
import type { AssignmentState, StaffSelection } from "./model";


interface StaffPickerProps {
  label: string;
  value: StaffSelection | null;
  state: AssignmentState;
  onChange: (staff: StaffSelection | null, state: AssignmentState) => void;
  searchStaff?: (query: string) => Promise<AdminStaffMember[]>;
}

async function defaultSearch(query: string): Promise<AdminStaffMember[]> {
  const page = await listAdminStaff(query);
  return page.items;
}

export function StaffPicker({
  label,
  value,
  state,
  onChange,
  searchStaff = defaultSearch,
}: StaffPickerProps) {
  const listId = useId();
  const requestNumber = useRef(0);
  const [query, setQuery] = useState(state === "no_officer_available" ? "NOA" : value?.display_name_snapshot ?? "");
  const [items, setItems] = useState<AdminStaffMember[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setQuery(state === "no_officer_available" ? "NOA" : value?.display_name_snapshot ?? "");
  }, [state, value]);

  async function runSearch(nextQuery: string) {
    const current = ++requestNumber.current;
    setLoading(true);
    try {
      const results = await searchStaff(nextQuery);
      if (current === requestNumber.current) {
        setItems(results.filter((item) => item.isActive));
        setActiveIndex(-1);
      }
    } finally {
      if (current === requestNumber.current) setLoading(false);
    }
  }

  function choose(item: AdminStaffMember) {
    onChange({ staff_id: item.staffId, display_name_snapshot: item.displayName }, "assigned");
    setQuery(item.displayName);
    setOpen(false);
  }

  function clear() {
    onChange(null, "unassigned");
    setQuery("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => Math.min(current + 1, items.length));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      if (activeIndex < items.length) choose(items[activeIndex]);
      else {
        onChange(null, "no_officer_available");
        setQuery("NOA");
        setOpen(false);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="staff-picker">
      <input
        type="search"
        role="combobox"
        aria-label={label}
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={open}
        aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        value={query}
        placeholder="Search name or employee #"
        onFocus={() => {
          setOpen(true);
          void runSearch(value ? "" : query);
        }}
        onChange={(event) => {
          const next = event.target.value;
          setQuery(next);
          setOpen(true);
          if (!next) clear();
          void runSearch(next);
        }}
        onKeyDown={handleKeyDown}
      />
      {open ? (
        <div id={listId} className="staff-picker-options" role="listbox" aria-label={`${label} choices`}>
          {items.map((item, index) => (
            <button
              key={item.staffId}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={activeIndex === index}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(item)}
            >
              <strong>{item.displayName}</strong>
              <small>{item.employeeNumber}{item.shift ? ` · ${item.shift} Shift` : ""}</small>
            </button>
          ))}
          <button
            id={`${listId}-${items.length}`}
            role="option"
            aria-selected={activeIndex === items.length}
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              onChange(null, "no_officer_available");
              setQuery("NOA");
              setOpen(false);
            }}
          ><strong>No Officer Available (NOA)</strong><small>Leave the post visibly unfilled</small></button>
          {loading ? <span className="staff-picker-loading">Searching…</span> : null}
          {!loading && !items.length ? <span className="staff-picker-loading">No matching active staff.</span> : null}
        </div>
      ) : null}
    </div>
  );
}
