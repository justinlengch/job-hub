
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface StatusCardProps {
  title: string;
  count: number;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  highlighted?: boolean;
}

const StatusCard = ({ title, count, icon: Icon, color, bgColor, highlighted = false }: StatusCardProps) => {
  return (
    <Card className={`hover:shadow-lg transition-shadow duration-200 ${highlighted ? 'ring-2 ring-offset-1 ring-indigo-500' : ''}`}>
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
