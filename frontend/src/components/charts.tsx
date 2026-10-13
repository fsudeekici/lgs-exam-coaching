import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DayQuestions, ExamPoint } from '../api'
import { formatDate, formatNet, formatShortDate, formatWeekday } from '../format'

// The student's own data is always blue; anything it is compared against is gray.
const STUDENT = '#2a78d6'
const COMPARISON = '#898781'
const GRID = '#e1e0d9'
const AXIS = '#c3c2b7'
const TICK = { fill: '#6b6a65', fontSize: 12 }

const tooltipProps = {
  formatter: (value: unknown) => formatNet(Number(value)),
  contentStyle: { borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13 },
  labelStyle: { color: '#0f172a', fontWeight: 600, marginBottom: 2 },
  itemStyle: { color: '#334155' },
}

interface TrendProps {
  /** Exams, oldest first. */
  exams: ExamPoint[]
  /** Which net to plot for an exam; undefined leaves a gap. */
  value: (exam: ExamPoint) => number | undefined
  label: string
  /** Fixed y-axis range. */
  domain: [number, number]
  ticks?: number[]
  height: number
  /** Print the latest value next to the last point. */
  labelLast?: boolean
}

/** One net over the student's exams. X positions are exams in date order, not a time scale. */
export function NetTrendChart({ exams, value, label, domain, ticks, height, labelLast }: TrendProps) {
  const data = exams.map((exam) => ({ id: String(exam.exam_id), net: value(exam) }))
  const byId = new Map(exams.map((exam) => [String(exam.exam_id), exam]))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 24, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="id"
          tickFormatter={(id) => formatShortDate(byId.get(id)!.exam_date)}
          tick={TICK}
          tickLine={false}
          axisLine={{ stroke: AXIS }}
          padding={{ left: 16, right: 16 }}
          minTickGap={12}
        />
        <YAxis domain={domain} ticks={ticks} tick={TICK} tickLine={false} axisLine={false} width={32} />
        <Tooltip
          {...tooltipProps}
          cursor={{ stroke: AXIS }}
          labelFormatter={(id) => {
            const exam = byId.get(String(id))
            return exam ? `${exam.name} · ${formatDate(exam.exam_date)}` : ''
          }}
        />
        <Line
          name={label}
          dataKey="net"
          stroke={STUDENT}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          dot={{ r: 4, fill: STUDENT, stroke: '#fff', strokeWidth: 2 }}
          activeDot={{ r: 5, fill: STUDENT, stroke: '#fff', strokeWidth: 2 }}
          isAnimationActive={false}
          label={
            labelLast
              ? ({ x, y, index, value: net }) =>
                  index === data.length - 1 && net != null ? (
                    <text x={Number(x)} y={Number(y) - 10} textAnchor="middle" fontSize={12} fontWeight={600} fill="#0f172a">
                      {formatNet(Number(net))}
                    </text>
                  ) : (
                    <g />
                  )
              : undefined
          }
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

interface AverageRow {
  subject: string
  student: number
  average: number
}

/** The student's average net per subject next to the average of everyone on the same exams. */
export function AverageComparisonChart({ rows, height }: { rows: AverageRow[]; height: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="30%">
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="subject" tick={TICK} tickLine={false} axisLine={{ stroke: AXIS }} />
        <YAxis domain={[0, 20]} ticks={[0, 5, 10, 15, 20]} tick={TICK} tickLine={false} axisLine={false} width={32} />
        <Tooltip {...tooltipProps} cursor={{ fill: '#f1f5f9' }} />
        <Legend
          verticalAlign="top"
          align="left"
          iconType="square"
          iconSize={10}
          itemSorter={null}
          wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
          formatter={(name) => <span style={{ color: '#334155' }}>{name}</span>}
        />
        <Bar name="Öğrenci" dataKey="student" fill={STUDENT} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
        <Bar
          name="Tüm öğrenciler"
          dataKey="average"
          fill={COMPARISON}
          radius={[4, 4, 0, 0]}
          maxBarSize={24}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Questions solved per day. `axis` picks the day labels: weekday names for a week, dates for longer periods. */
export function DailyQuestionsChart({ days, height, axis }: { days: DayQuestions[]; height: number; axis: 'weekday' | 'date' }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={axis === 'date' ? 2 : '10%'}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="day"
          tickFormatter={axis === 'weekday' ? formatWeekday : formatShortDate}
          tick={TICK}
          tickLine={false}
          axisLine={{ stroke: AXIS }}
          interval={axis === 'weekday' ? 0 : 'preserveStartEnd'}
          minTickGap={16}
        />
        <YAxis allowDecimals={false} tick={TICK} tickLine={false} axisLine={false} width={32} />
        <Tooltip
          contentStyle={tooltipProps.contentStyle}
          labelStyle={tooltipProps.labelStyle}
          itemStyle={tooltipProps.itemStyle}
          cursor={{ fill: '#f1f5f9' }}
          labelFormatter={(day) => formatDate(String(day))}
        />
        <Bar name="Çözülen soru" dataKey="solved" fill={STUDENT} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
