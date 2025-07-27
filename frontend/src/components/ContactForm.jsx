import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, CheckCircle, AlertCircle, Send, User, Mail, Building, Phone, MessageSquare } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const ContactForm = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    message: '',
    preferred_contact_method: '',
    consent_marketing: false,
    consent_data_processing: false
  })

  const [formState, setFormState] = useState({
    isSubmitting: false,
    isSubmitted: false,
    error: null,
    validationErrors: {},
    submissionStartTime: null,
    eventId: null,
    correlationId: null
  })

  const [sessionId] = useState(() => `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  // Real-time validation
  const validateField = (name, value) => {
    const errors = {}
    
    switch (name) {
      case 'name':
        if (!value.trim()) errors.name = 'Name is required'
        else if (value.trim().length < 2) errors.name = 'Name must be at least 2 characters'
        else if (value.trim().length > 100) errors.name = 'Name must be less than 100 characters'
        break
      
      case 'email':
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!value.trim()) errors.email = 'Email is required'
        else if (!emailRegex.test(value)) errors.email = 'Please enter a valid email address'
        break
      
      case 'company':
        if (!value.trim()) errors.company = 'Company is required'
        else if (value.trim().length < 2) errors.company = 'Company name must be at least 2 characters'
        else if (value.trim().length > 100) errors.company = 'Company name must be less than 100 characters'
        break
      
      case 'phone':
        if (value && !/^[\+]?[1-9][\d]{0,15}$/.test(value.replace(/[\s\-\(\)]/g, ''))) {
          errors.phone = 'Please enter a valid phone number'
        }
        break
      
      case 'message':
        if (!value.trim()) errors.message = 'Message is required'
        else if (value.trim().length < 10) errors.message = 'Message must be at least 10 characters'
        else if (value.trim().length > 2000) errors.message = 'Message must be less than 2000 characters'
        break
      
      case 'preferred_contact_method':
        if (!value) errors.preferred_contact_method = 'Please select a preferred contact method'
        break
    }
    
    return errors
  }

  const handleInputChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }))
    
    // Clear validation errors for this field
    if (formState.validationErrors[name]) {
      setFormState(prev => ({
        ...prev,
        validationErrors: {
          ...prev.validationErrors,
          [name]: undefined
        }
      }))
    }
  }

  const handleBlur = (name, value) => {
    const fieldErrors = validateField(name, value)
    setFormState(prev => ({
      ...prev,
      validationErrors: {
        ...prev.validationErrors,
        ...fieldErrors
      }
    }))
  }

  const validateForm = () => {
    const errors = {}
    
    Object.keys(formData).forEach(key => {
      if (key !== 'phone') { // Phone is optional
        const fieldErrors = validateField(key, formData[key])
        Object.assign(errors, fieldErrors)
      }
    })

    // Check consent requirements
    if (!formData.consent_data_processing) {
      errors.consent_data_processing = 'Data processing consent is required'
    }

    return errors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    const submissionStartTime = Date.now()
    setFormState(prev => ({ 
      ...prev, 
      isSubmitting: true, 
      error: null, 
      submissionStartTime 
    }))

    // Validate form
    const validationErrors = validateForm()
    if (Object.keys(validationErrors).length > 0) {
      setFormState(prev => ({
        ...prev,
        isSubmitting: false,
        validationErrors
      }))
      return
    }

    try {
      const submissionDuration = Date.now() - submissionStartTime
      
      const payload = {
        form_data: formData,
        metadata: {
          session_id: sessionId,
          form_version: '1.0.0',
          submission_duration_ms: submissionDuration
        }
      }

      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })

      const result = await response.json()

      if (response.ok) {
        setFormState(prev => ({
          ...prev,
          isSubmitting: false,
          isSubmitted: true,
          eventId: result.event_id,
          correlationId: result.correlation_id
        }))
      } else {
        throw new Error(result.error || 'Failed to submit form')
      }
    } catch (error) {
      setFormState(prev => ({
        ...prev,
        isSubmitting: false,
        error: error.message
      }))
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      company: '',
      phone: '',
      message: '',
      preferred_contact_method: '',
      consent_marketing: false,
      consent_data_processing: false
    })
    setFormState({
      isSubmitting: false,
      isSubmitted: false,
      error: null,
      validationErrors: {},
      submissionStartTime: null,
      eventId: null,
      correlationId: null
    })
  }

  if (formState.isSubmitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto p-6"
      >
        <Card className="border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800">
          <CardHeader className="text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
            >
              <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
            </motion.div>
            <CardTitle className="text-2xl text-green-800 dark:text-green-200">
              Thank You!
            </CardTitle>
            <CardDescription className="text-green-700 dark:text-green-300">
              Your message has been successfully submitted and is being processed through our event-driven architecture.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border">
              <h4 className="font-semibold mb-2">Submission Details:</h4>
              <div className="text-sm space-y-1 text-gray-600 dark:text-gray-400">
                <p><strong>Event ID:</strong> {formState.eventId}</p>
                <p><strong>Correlation ID:</strong> {formState.correlationId}</p>
                <p><strong>Status:</strong> Processing in background</p>
              </div>
            </div>
            <div className="text-center">
              <Button onClick={resetForm} variant="outline">
                Submit Another Message
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto p-6"
    >
      <Card className="shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Contact Us
          </CardTitle>
          <CardDescription className="text-lg">
            Experience our event-driven architecture in action. Your submission triggers automated workflows and real-time processing.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Alert */}
            <AnimatePresence>
              {formState.error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{formState.error}</AlertDescription>
                  </Alert>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="name" className="flex items-center gap-2">
                <User className="w-4 h-4" />
                Full Name *
              </Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                onBlur={(e) => handleBlur('name', e.target.value)}
                placeholder="Enter your full name"
                className={formState.validationErrors.name ? 'border-red-500' : ''}
                disabled={formState.isSubmitting}
              />
              {formState.validationErrors.name && (
                <p className="text-sm text-red-600">{formState.validationErrors.name}</p>
              )}
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email" className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Email Address *
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                onBlur={(e) => handleBlur('email', e.target.value)}
                placeholder="Enter your email address"
                className={formState.validationErrors.email ? 'border-red-500' : ''}
                disabled={formState.isSubmitting}
              />
              {formState.validationErrors.email && (
                <p className="text-sm text-red-600">{formState.validationErrors.email}</p>
              )}
            </div>

            {/* Company Field */}
            <div className="space-y-2">
              <Label htmlFor="company" className="flex items-center gap-2">
                <Building className="w-4 h-4" />
                Company *
              </Label>
              <Input
                id="company"
                type="text"
                value={formData.company}
                onChange={(e) => handleInputChange('company', e.target.value)}
                onBlur={(e) => handleBlur('company', e.target.value)}
                placeholder="Enter your company name"
                className={formState.validationErrors.company ? 'border-red-500' : ''}
                disabled={formState.isSubmitting}
              />
              {formState.validationErrors.company && (
                <p className="text-sm text-red-600">{formState.validationErrors.company}</p>
              )}
            </div>

            {/* Phone Field */}
            <div className="space-y-2">
              <Label htmlFor="phone" className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                Phone Number
              </Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => handleInputChange('phone', e.target.value)}
                onBlur={(e) => handleBlur('phone', e.target.value)}
                placeholder="Enter your phone number (optional)"
                className={formState.validationErrors.phone ? 'border-red-500' : ''}
                disabled={formState.isSubmitting}
              />
              {formState.validationErrors.phone && (
                <p className="text-sm text-red-600">{formState.validationErrors.phone}</p>
              )}
            </div>

            {/* Preferred Contact Method */}
            <div className="space-y-2">
              <Label htmlFor="contact-method">Preferred Contact Method *</Label>
              <Select
                value={formData.preferred_contact_method}
                onValueChange={(value) => handleInputChange('preferred_contact_method', value)}
                disabled={formState.isSubmitting}
              >
                <SelectTrigger className={formState.validationErrors.preferred_contact_method ? 'border-red-500' : ''}>
                  <SelectValue placeholder="Select preferred contact method" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="phone">Phone</SelectItem>
                  <SelectItem value="both">Both Email and Phone</SelectItem>
                </SelectContent>
              </Select>
              {formState.validationErrors.preferred_contact_method && (
                <p className="text-sm text-red-600">{formState.validationErrors.preferred_contact_method}</p>
              )}
            </div>

            {/* Message Field */}
            <div className="space-y-2">
              <Label htmlFor="message" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Message *
              </Label>
              <Textarea
                id="message"
                value={formData.message}
                onChange={(e) => handleInputChange('message', e.target.value)}
                onBlur={(e) => handleBlur('message', e.target.value)}
                placeholder="Tell us about your interest in our solutions..."
                rows={4}
                className={formState.validationErrors.message ? 'border-red-500' : ''}
                disabled={formState.isSubmitting}
              />
              <div className="flex justify-between text-sm text-gray-500">
                <span>{formState.validationErrors.message && (
                  <span className="text-red-600">{formState.validationErrors.message}</span>
                )}</span>
                <span>{formData.message.length}/2000</span>
              </div>
            </div>

            {/* Consent Checkboxes */}
            <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex items-start space-x-2">
                <Checkbox
                  id="consent-processing"
                  checked={formData.consent_data_processing}
                  onCheckedChange={(checked) => handleInputChange('consent_data_processing', checked)}
                  disabled={formState.isSubmitting}
                />
                <Label htmlFor="consent-processing" className="text-sm leading-relaxed">
                  I consent to the processing of my personal data for the purpose of responding to my inquiry. *
                </Label>
              </div>
              {formState.validationErrors.consent_data_processing && (
                <p className="text-sm text-red-600 ml-6">{formState.validationErrors.consent_data_processing}</p>
              )}
              
              <div className="flex items-start space-x-2">
                <Checkbox
                  id="consent-marketing"
                  checked={formData.consent_marketing}
                  onCheckedChange={(checked) => handleInputChange('consent_marketing', checked)}
                  disabled={formState.isSubmitting}
                />
                <Label htmlFor="consent-marketing" className="text-sm leading-relaxed">
                  I would like to receive marketing communications about your products and services.
                </Label>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full h-12 text-lg"
              disabled={formState.isSubmitting}
            >
              {formState.isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default ContactForm

