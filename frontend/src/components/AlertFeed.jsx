import { clockTime } from '../utils/format'
import './AlertFeed.css'

export default function AlertFeed({ events }) {
  return (
    <section className="alert-feed panel">
      <span className="panel-title">Alert Timeline</span>
      <div className="alert-feed-list">
        {events.map((event) => (
          <div className="alert-feed-item" key={event.id}>
            <span className="alert-feed-time mono">{clockTime(event.timestamp)}</span>
            <span className="alert-feed-message">{event.message}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
