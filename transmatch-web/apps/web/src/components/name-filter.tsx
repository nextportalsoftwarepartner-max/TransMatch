"use client";

import { useState, type ReactNode } from "react";
import { Button, Card, TextField } from "./ui";

interface NameFilterProps {
  label: string;
  /** Called with the trimmed text on Search, and with "" on Reset. */
  onSearch: (name: string) => void;
  /** Extra filter controls shown after the name box. */
  children?: ReactNode;
  onReset?: () => void;
}

/** "Filter Criteria" card with one name box, used by the administration screens. */
export function NameFilter({ label, onSearch, children, onReset }: NameFilterProps) {
  const [name, setName] = useState("");
  return (
    <Card title="Filter Criteria">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          onSearch(name.trim());
        }}
      >
        <TextField label={label} value={name} onChange={setName} className="w-72" />
        {children}
        <Button type="submit">Search</Button>
        <Button
          variant="secondary"
          onClick={() => {
            setName("");
            onReset?.();
            onSearch("");
          }}
        >
          Reset
        </Button>
      </form>
    </Card>
  );
}
