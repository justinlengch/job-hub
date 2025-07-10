
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimelineEvent as TimelineEventType } from "@/types/application";
import { Calendar, Building2 } from "lucide-react";

interface TimelineEventProps {
  event: TimelineEventType;
}

const statusColors = {
  applied: "bg-blue-100 text-blue-800",
  'in-progress': "bg-yellow-100 text-yellow-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800"
};

const TimelineEventComponent = ({ event }: TimelineEventProps) => {
  return (
    <Card className="p-4 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <span className="font-semibold text-sm">{event.company}</span>
            <Badge className={`text-xs ${statusColors[event.status]}`}>
              {event.status.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-1">{event.position}</p>
          <p className="text-sm">{event.description}</p>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          <span>{new Date(event.date).toLocaleDateString()}</span>
        </div>
      </div>
    </Card>
  );
};

export default TimelineEventComponent;
