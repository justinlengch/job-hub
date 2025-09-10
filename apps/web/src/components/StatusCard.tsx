
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface StatusCardProps {
  title: string;
  count: number;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  highlighted?: boolean;
  tinted?: boolean;
  accent?: "indigo" | "amber" | "emerald" | "rose" | "sky";
}

const StatusCard = ({
  title,
  count,
  icon: Icon,
  color,
  bgColor,
  highlighted = false,
  tinted = false,
  accent = "indigo",
}: StatusCardProps) => {
  const accents = {
    indigo: { ring: "ring-indigo-500", border: "border-indigo-500", bg: "bg-indigo-100" },
    amber: { ring: "ring-amber-500", border: "border-amber-500", bg: "bg-amber-100" },
    emerald: { ring: "ring-emerald-500", border: "border-emerald-500", bg: "bg-emerald-100" },
    rose: { ring: "ring-rose-500", border: "border-rose-500", bg: "bg-rose-100" },
    sky: { ring: "ring-sky-500", border: "border-sky-500", bg: "bg-sky-100" },
  } as const;
  const a = accents[accent] ?? accents.indigo;
  const baseCardClass = "hover:shadow-lg transition-shadow duration-200";
  const ringClass = highlighted ? `ring-2 ring-offset-1 ${a.ring}` : "";
  const tintClass = (highlighted || tinted) ? `border-2 ${a.border} ${a.bg}` : "";

  return (
    <Card
      className={`${baseCardClass} ${ringClass} ${tintClass}`}
    >
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold">{count}</p>
          </div>
          <div className={`p-3 rounded-full ${bgColor}`}>
            <Icon className={`h-6 w-6 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default StatusCard;
