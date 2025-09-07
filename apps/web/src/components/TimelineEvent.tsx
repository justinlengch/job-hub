import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimelineEvent as TimelineEventType } from "@/types/application";
import { Calendar, Building2, ExternalLink } from "lucide-react";

interface TimelineEventProps {
  event: TimelineEventType;
}

const eventTypeColors = {
  APPLICATION_SUBMITTED: "bg-blue-100 text-blue-800",
  APPLICATION_RECEIVED: "bg-blue-100 text-blue-800",
  APPLICATION_VIEWED: "bg-blue-100 text-blue-800",
  APPLICATION_REVIEWED: "bg-purple-100 text-purple-800",
  ASSESSMENT_RECEIVED: "bg-purple-100 text-purple-800",
  ASSESSMENT_COMPLETED: "bg-purple-100 text-purple-800",
  INTERVIEW_SCHEDULED: "bg-yellow-100 text-yellow-800",
  INTERVIEW_COMPLETED: "bg-yellow-100 text-yellow-800",
  REFERENCE_REQUESTED: "bg-orange-100 text-orange-800",
  OFFER_RECEIVED: "bg-green-100 text-green-800",
  OFFER_ACCEPTED: "bg-green-100 text-green-800",
  OFFER_DECLINED: "bg-red-100 text-red-800",
  APPLICATION_REJECTED: "bg-red-100 text-red-800",
  APPLICATION_WITHDRAWN: "bg-gray-100 text-gray-800",
};

const formatEventType = (eventType: string) => {
  return eventType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
};

const TimelineEventComponent = ({ event }: TimelineEventProps) => {
  return (
    <Card className="p-4 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <span className="font-semibold text-sm">
              {event.company || "Unknown Company"}
            </span>
            <Badge
              className={`text-xs ${
                eventTypeColors[event.event_type] || "bg-gray-100 text-gray-800"
              }`}
            >
              {formatEventType(event.event_type)}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-1">
            {event.role || "Unknown Role"}
          </p>
          <p className="text-sm">{event.description}</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{new Date(event.email_received_at || event.event_date).toLocaleDateString()}</span>
          </div>
          {event.gmail_url && (
            <a
              href={event.gmail_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline inline-flex items-center gap-1"
              title="Open original email in Gmail"
            >
              View email
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </Card>
  );
};

export default TimelineEventComponent;
