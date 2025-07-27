import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  Zap, 
  Database, 
  Mail, 
  Workflow, 
  Shield, 
  BarChart3, 
  Clock, 
  CheckCircle,
  ArrowRight,
  Github,
  ExternalLink
} from 'lucide-react'
import ContactForm from './components/ContactForm'
import './App.css'

function App() {
  const [showDemo, setShowDemo] = useState(false)
  const [stats, setStats] = useState({
    eventsProcessed: 0,
    avgResponseTime: 0,
    systemHealth: 'healthy'
  })

  // Simulate real-time stats updates
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(prev => ({
        eventsProcessed: prev.eventsProcessed + Math.floor(Math.random() * 3),
        avgResponseTime: 150 + Math.floor(Math.random() * 100),
        systemHealth: Math.random() > 0.1 ? 'healthy' : 'degraded'
      }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const features = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: "Event-Driven Architecture",
      description: "Asynchronous processing with Apache Kafka for high throughput and reliability"
    },
    {
      icon: <Database className="w-6 h-6" />,
      title: "Event Sourcing",
      description: "Complete audit trail with immutable events and UUIDv7 for natural ordering"
    },
    {
      icon: <Mail className="w-6 h-6" />,
      title: "Automated Email Processing",
      description: "Mustache templates with HTML/text generation and delivery tracking"
    },
    {
      icon: <Workflow className="w-6 h-6" />,
      title: "Intelligent Workflows",
      description: "Multi-step business process automation with compensation logic"
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "Security & Compliance",
      description: "GDPR compliance, TLS encryption, and comprehensive audit logging"
    },
    {
      icon: <BarChart3 className="w-6 h-6" />,
      title: "Full Observability",
      description: "Prometheus metrics, distributed tracing, and structured logging"
    }
  ]

  const architectureFlow = [
    { step: 1, title: "Form Submission", description: "User submits contact form" },
    { step: 2, title: "Event Publishing", description: "ContactFormSubmitted event to Kafka" },
    { step: 3, title: "Parallel Processing", description: "Mailer & Workflow services consume events" },
    { step: 4, title: "Email Dispatch", description: "Personalized emails sent via SMTP" },
    { step: 5, title: "CRM Integration", description: "Lead created with automated workflow" },
    { step: 6, title: "Complete Traceability", description: "End-to-end correlation tracking" }
  ]

  if (showDemo) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="container mx-auto py-8">
          <div className="mb-8 text-center">
            <Button 
              variant="outline" 
              onClick={() => setShowDemo(false)}
              className="mb-4"
            >
              ← Back to Overview
            </Button>
            <h1 className="text-4xl font-bold mb-2">Live Demo</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Experience the event-driven architecture in real-time
            </p>
          </div>
          <ContactForm />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Zap className="w-8 h-8 text-blue-600" />
                <h1 className="text-2xl font-bold">Event-Driven PoC</h1>
              </div>
              <Badge variant="secondary" className="hidden sm:inline-flex">
                v1.0.0
              </Badge>
            </div>
            <div className="flex items-center space-x-4">
              <div className="hidden md:flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${stats.systemHealth === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  <span>System {stats.systemHealth}</span>
                </div>
                <Separator orientation="vertical" className="h-4" />
                <span>{stats.eventsProcessed} events processed</span>
                <Separator orientation="vertical" className="h-4" />
                <span>{stats.avgResponseTime}ms avg response</span>
              </div>
              <Button onClick={() => setShowDemo(true)} className="bg-gradient-to-r from-blue-600 to-purple-600">
                Try Live Demo
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent">
              Event-Driven Architecture
            </h1>
            <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-8 max-w-4xl mx-auto">
              A comprehensive proof-of-concept demonstrating modern microservices patterns, 
              event sourcing, and distributed system observability with real-time processing.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                size="lg" 
                onClick={() => setShowDemo(true)}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-lg px-8 py-3"
              >
                Experience the Demo
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
              <Button size="lg" variant="outline" className="text-lg px-8 py-3">
                <Github className="w-5 h-5 mr-2" />
                View Source Code
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Architecture Flow */}
      <section className="py-16 bg-white/50 dark:bg-gray-800/50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">How It Works</h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Follow the journey of a contact form submission through our event-driven architecture
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {architectureFlow.map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="h-full hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                        {item.step}
                      </div>
                      <CardTitle className="text-lg">{item.title}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600 dark:text-gray-400">{item.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Key Features</h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Built with production-ready patterns and modern technologies
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="h-full hover:shadow-lg transition-shadow group">
                  <CardHeader>
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg text-white group-hover:scale-110 transition-transform">
                        {feature.icon}
                      </div>
                      <CardTitle className="text-lg">{feature.title}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600 dark:text-gray-400">{feature.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology Stack */}
      <section className="py-16 bg-white/50 dark:bg-gray-800/50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Technology Stack</h2>
            <p className="text-gray-600 dark:text-gray-400">
              Modern, scalable technologies for enterprise-grade solutions
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              'React 18', 'Flask', 'Apache Kafka', 'PostgreSQL', 
              'Docker', 'Prometheus', 'Grafana', 'OpenTelemetry',
              'Mustache', 'TailwindCSS', 'Python 3.11', 'Node.js'
            ].map((tech, index) => (
              <motion.div
                key={tech}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
              >
                <Badge variant="secondary" className="w-full justify-center py-2 hover:bg-primary hover:text-primary-foreground transition-colors">
                  {tech}
                </Badge>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-bold mb-6">Ready to Experience It?</h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
              Submit a contact form and watch as it triggers our complete event-driven workflow 
              with real-time processing, automated emails, and CRM integration.
            </p>
            <Button 
              size="lg" 
              onClick={() => setShowDemo(true)}
              className="bg-gradient-to-r from-blue-600 to-purple-600 text-lg px-8 py-3"
            >
              Start the Demo
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <Zap className="w-6 h-6 text-blue-600" />
              <span className="font-semibold">Event-Driven Architecture PoC</span>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
              <span>Built with modern technologies</span>
              <Separator orientation="vertical" className="h-4" />
              <span>Production-ready patterns</span>
              <Separator orientation="vertical" className="h-4" />
              <span>© 2025 Manus AI</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
