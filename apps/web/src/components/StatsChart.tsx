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
  const labelRadius = outerRadius + 14;
  const x = cx + labelRadius * Math.cos(-midAngle * RADIAN);
  const y = cy + labelRadius * Math.sin(-midAngle * RADIAN);
  const padding = 4;
  const finalX = x + (x > cx ? padding : -padding);

  return (
    <text
      x={finalX}
      y={y}
      fill="#555"
      fontSize={14}
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

type PieLabelLineProps = {
  cx: number;
  cy: number;
  midAngle: number;
  outerRadius: number;
};

const renderLabelLine = ({ cx, cy, midAngle, outerRadius }: PieLabelLineProps) => {
  const gap = 6; // leave a small gap from the pie
  const lineLen = 14; // length of the leader line segment
  const startR = outerRadius + gap;
  const endR = startR + lineLen;

  const x1 = cx + startR * Math.cos(-midAngle * RADIAN);
  const y1 = cy + startR * Math.sin(-midAngle * RADIAN);
  const x2 = cx + endR * Math.cos(-midAngle * RADIAN);
  const y2 = cy + endR * Math.sin(-midAngle * RADIAN);

  return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#999" strokeWidth={1} />;
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
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={barData} margin={{ top: 20, bottom: 20 }}>
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
          <ResponsiveContainer width="100%" height={420}>
            <PieChart>
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                iconSize={14}
                wrapperStyle={{ fontSize: 14, lineHeight: "28px" }}
              />
              <Pie
                data={pieData}
                nameKey="name"
                cx="46%"
                cy="50%"
                paddingAngle={2}
                outerRadius={130}
                labelLine={false}
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
