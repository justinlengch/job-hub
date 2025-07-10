
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { JobApplication } from "@/types/application";

interface FilterControlsProps {
  selectedStatus: JobApplication['status'] | 'all';
  onStatusChange: (status: JobApplication['status'] | 'all') => void;
}

const statusOptions: { value: JobApplication['status'] | 'all'; label: string; count?: number }[] = [
  { value: 'all', label: 'All Applications' },
  { value: 'applied', label: 'Applied' },
  { value: 'in-progress', label: 'In Progress' },
  { value: 'offer', label: 'Offers' },
  { value: 'rejected', label: 'Rejected' }
];

const FilterControls = ({ selectedStatus, onStatusChange }: FilterControlsProps) => {
  return (
    <div className="flex flex-wrap gap-2 p-4 bg-muted/30 rounded-lg">
      {statusOptions.map((option) => (
        <Button
          key={option.value}
          variant={selectedStatus === option.value ? "default" : "outline"}
          size="sm"
          onClick={() => onStatusChange(option.value)}
          className="flex items-center gap-2"
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
};

export default FilterControls;
