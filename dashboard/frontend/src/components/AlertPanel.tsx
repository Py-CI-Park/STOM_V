import { Alert, AlertDescription, AlertTitle } from './ui/alert'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { Alert as AlertType } from '../types'

interface Props {
  alerts: AlertType[]
}

export default function AlertPanel({ alerts }: Props) {
  if (alerts.length === 0) return null

  return (
    <div className="space-y-2">
      {alerts.map((alert, index) => (
        <Alert key={index} variant={alert.type === 'profit' ? 'default' : 'destructive'}>
          {alert.type === 'profit' ? (
            <TrendingUp className="h-4 w-4" />
          ) : (
            <TrendingDown className="h-4 w-4" />
          )}
          <AlertTitle>{alert.type === 'profit' ? '수익 알림' : '손실 알림'}</AlertTitle>
          <AlertDescription>{alert.message}</AlertDescription>
        </Alert>
      ))}
    </div>
  )
}
