import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ConfigSettings() {
  const [concurrency, setConcurrency] = useState(1);
  const [confidence, setConfidence] = useState(99);
  const [maxRounds, setMaxRounds] = useState(3);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    console.log("Save config:", { concurrency, confidence, maxRounds });
  }

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="concurrency">Concurrency Limit</Label>
          <Input
            id="concurrency"
            type="number"
            min={1}
            max={10}
            value={concurrency}
            onChange={(e) => setConcurrency(Number(e.target.value))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confidence">Confidence Threshold</Label>
          <Input
            id="confidence"
            type="number"
            min={0}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="max-rounds">Max Follow-up Rounds</Label>
          <Input
            id="max-rounds"
            type="number"
            min={1}
            max={20}
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
          />
        </div>
      </div>
      <Button type="submit" size="sm">
        Save
      </Button>
    </form>
  );
}
