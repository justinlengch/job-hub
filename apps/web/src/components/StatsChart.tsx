
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { StatusCounts } from "@/types/application";

interface StatsChartProps {
  statusCounts: StatusCounts;
}

const COLORS = {
  applied: '#3b82f6',
  'in-progress': '#f59e0b',
  offer: '#10b981',
  rejected: '#ef4444'
};

const StatsChart = ({ statusCounts }: StatsChartProps) => {
  const barData = [
    { name: 'Applied', value: statusCounts.applied, color: COLORS.applied },
    { name: 'In Progress', value: statusCounts['in-progress'], color: COLORS['in-progress'] },
    { name: 'Offers', value: statusCounts.offer, color: COLORS.offer },
    { name: 'Rejected', value: statusCounts.rejected, color: COLORS.rejected }
  ];

  const pieData = barData.filter(item => item.value > 0);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Application Status Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
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
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
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
