import { useState, useRef } from 'react'

const ACCIDENT_DESCRIPTIONS = [
  'Rear-end collision',
  'Multi-vehicle accident',
  'Blocked lane',
  'Minor fender bender',
  'Vehicle breakdown',
  'Debris on road',
  'Other'
]

const SEVERITIES = [
  { value: 'minor', label: 'Minor' },
  { value: 'medium', label: 'Medium' },
  { value: 'major', label: 'Major' }
]

function ReportPanel({active}) {
  const [description, setDescription] = useState(ACCIDENT_DESCRIPTIONS[0])
  const [customDescription, setCustomDescription] = useState('')
  const [severity, setSeverity] = useState('minor')
  const [reportMsg, setReportMsg] = useState('Help improve safety by reporting accidents.')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const formRef = useRef(null)

  const resetForm = () => {
    setDescription(ACCIDENT_DESCRIPTIONS[0])
    setCustomDescription('')
    setSeverity('minor')
    setReportMsg('Help improve safety by reporting accidents.')
  }

  const handleSubmit = async () => {
    if (isSubmitting) return

    setIsSubmitting(true)
    setReportMsg('Getting your location...')

    try {
      // Get current geolocation
      const position = await new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
          reject(new Error('Geolocation is not supported by your browser'))
          return
        }
        
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        })
      })

      const latitude = position.coords.latitude
      const longitude = position.coords.longitude

      setReportMsg('Submitting report...')

      // Determine final description
      const finalDescription = description === 'Other' ? customDescription.trim() : description

      if (!finalDescription) {
        setReportMsg('Please provide a description for "Other".')
        setIsSubmitting(false)
        return
      }

      // Submit to backend
      const response = await fetch('http://localhost:8010/pwa/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          latitude,
          longitude,
          severity,
          description: finalDescription
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      const data = await response.json()
      
      // Success - reset form
      resetForm()
      setReportMsg('Report submitted successfully. Thank you for helping keep our roads safe!')
      
      // Clear success message after 5 seconds
      setTimeout(() => {
        setReportMsg('Help improve safety by reporting accidents.')
      }, 5000)

    } catch (error) {
      console.error('Report submission error:', error)
      
      // Show error but keep form filled for retry
      if (error.message.includes('Geolocation')) {
        setReportMsg('Unable to get your location. Please enable location services and try again.')
      } else if (error.message.includes('Network') || error.message.includes('fetch')) {
        setReportMsg('Network error. Please check your connection and try again.')
      } else {
        setReportMsg(`Error: ${error.message}. Please try again.`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="reports-card">
      <article className="card">
        <h2>Report Accident</h2>
        <div className="body">
          <form ref={formRef} onSubmit={(e) => e.preventDefault()}>
            <div className="controls" style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              
              {/* Description dropdown */}
              <div>
                <label htmlFor="description-select" style={{ display: 'block', marginBottom: '0.3rem', fontSize: '0.9rem' }}>
                  Description
                </label>
                <select
                  id="description-select"
                  className="btn"
                  style={{ padding: '.45rem .6rem', width: '100%' }}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isSubmitting}
                >
                  {ACCIDENT_DESCRIPTIONS.map((desc) => (
                    <option key={desc} value={desc}>{desc}</option>
                  ))}
                </select>
              </div>

              {/* Custom description text input (shown when "Other" is selected) */}
              {description === 'Other' && (
                <div>
                  <label htmlFor="custom-description" style={{ display: 'block', marginBottom: '0.3rem', fontSize: '0.9rem' }}>
                    Describe the accident
                  </label>
                  <input
                    id="custom-description"
                    type="text"
                    className="btn"
                    style={{ padding: '.45rem .6rem', width: '100%' }}
                    placeholder="Enter description..."
                    value={customDescription}
                    onChange={(e) => setCustomDescription(e.target.value)}
                    disabled={isSubmitting}
                    maxLength={500}
                  />
                </div>
              )}

              {/* Severity dropdown */}
              <div>
                <label htmlFor="severity-select" style={{ display: 'block', marginBottom: '0.3rem', fontSize: '0.9rem' }}>
                  Severity
                </label>
                <select
                  id="severity-select"
                  className="btn"
                  style={{ padding: '.45rem .6rem', width: '100%' }}
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  disabled={isSubmitting}
                >
                  {SEVERITIES.map((sev) => (
                    <option key={sev.value} value={sev.value}>{sev.label}</option>
                  ))}
                </select>
              </div>

              {/* Submit button */}
              <button 
                className="btn" 
                onClick={handleSubmit}
                disabled={isSubmitting}
                style={{ marginTop: '0.4rem' }}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </form>

          {/* Status message */}
          <div style={{ 
            marginTop: '.8rem', 
            color: reportMsg.includes('Error') || reportMsg.includes('Unable') ? '#dc2626' : 'var(--muted)',
            fontSize: '0.9rem',
            lineHeight: '1.4'
          }}>
            {reportMsg}
          </div>
        </div>
      </article>
    </section>
  )
}

export default ReportPanel
