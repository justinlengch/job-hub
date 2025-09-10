import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { StatusCounts } from "@/types/application";

interface StatsChartProps {
  statusCounts: StatusCounts;
}

const COLORS = {
  APPLIED: "#3b82f6",
  ASSESSMENT: "#8b5cf6",
  INTERVIEW: "#f59e0b",
  OFFERED: "#10b981",
  ACCEPTED: "#059669",
  REJECTED: "#ef4444",
  WITHDRAWN: "#6b7280",
};

type PieLabelProps = {
  cx: number;
  cy: number;
  midAngle: number;
  outerRadius: number;
  percent: number;
  name: string;
};

const RADIAN = Math.PI / 180;
const renderCustomizedLabel = ({
  cx,
  cy,
  midAngle,
  outerRadius,
  percent,
  name,
}: PieLabelProps) => {
  const radius = outerRadius + 20;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#555"
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

type AxisTickProps = {
  x?: number;
  y?: number;
  payload?: { value: string };
};

const RenderXAxisTick = ({ x = 0, y = 0, payload }: AxisTickProps) => {
  const value = payload?.value ?? "";
  return (
    <g transform={`translate(${x},${y})`}>
      <text dy={16} textAnchor="end" fill="#666" transform="rotate(-30)">
        {value}
      </text>
    </g>
  );
};

const StatsChart = ({ statusCounts }: StatsChartProps) => {
  const barData = [
    { name: "Applied", value: statusCounts.APPLIED, color: COLORS.APPLIED },
    {
      name: "Assessment",
      value: statusCounts.ASSESSMENT,
      color: COLORS.ASSESSMENT,
    },
    {
      name: "Interview",
      value: statusCounts.INTERVIEW,
      color: COLORS.INTERVIEW,
    },
    { name: "Offered", value: statusCounts.OFFERED, color: COLORS.OFFERED },
    { name: "Accepted", value: statusCounts.ACCEPTED, color: COLORS.ACCEPTED },
    { name: "Rejected", value: statusCounts.REJECTED, color: COLORS.REJECTED },
    {
      name: "Withdrawn",
      value: statusCounts.WITHDRAWN,
      color: COLORS.WITHDRAWN,
    },
  ];

  const pieData = barData.filter((item) => item.value > 0);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Application Status Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData} margin={{ bottom: 48 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} tick={<RenderXAxisTick />} height={70} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#8884d8">
                {barData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Status Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Legend layout="vertical" align="right" verticalAlign="middle" />
              <Pie
                data={pieData}
                nameKey="name"
                cx="35%"
                cy="50%"
                paddingAngle={2}
                outerRadius={80}
                labelLine={{ stroke: "#999" }}
                label={renderCustomizedLabel}

                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};

export default StatsChart;
