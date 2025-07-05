import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { 
  School, 
  Users, 
  BookOpen, 
  GraduationCap, 
  FileText, 
  Settings, 
  LogOut, 
  User, 
  BarChart3,
  Calendar,
  Trophy,
  TrendingUp,
  Eye,
  Download,
  Bell,
  Menu,
  X
} from 'lucide-react'
import './App.css'

// Authentication Context
const AuthContext = createContext()

const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// API Service
const API_BASE_URL = 'http://localhost:5000/api'

const apiService = {
  async login(credentials) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    })
    return response.json()
  },

  async logout(token) {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async getDashboard(token, role) {
    const response = await fetch(`${API_BASE_URL}/${role}/dashboard`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async getResults(token, role, params = {}) {
    const queryString = new URLSearchParams(params).toString()
    const response = await fetch(`${API_BASE_URL}/${role}/results?${queryString}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  }
}

// Auth Provider Component
function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const storedUser = localStorage.getItem('user')
    if (storedUser && token) {
      setUser(JSON.parse(storedUser))
    }
    setLoading(false)
  }, [token])

  const login = async (credentials) => {
    try {
      const response = await apiService.login(credentials)
      if (response.success) {
        const { user: userData, access_token } = response.data
        setUser(userData)
        setToken(access_token)
        localStorage.setItem('user', JSON.stringify(userData))
        localStorage.setItem('token', access_token)
        return { success: true }
      } else {
        return { success: false, message: response.message }
      }
    } catch (error) {
      return { success: false, message: 'Login failed. Please try again.' }
    }
  }

  const logout = async () => {
    try {
      if (token) {
        await apiService.logout(token)
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setUser(null)
      setToken(null)
      localStorage.removeItem('user')
      localStorage.removeItem('token')
    }
  }

  const value = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!user && !!token
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// Login Component
function LoginPage() {
  const [credentials, setCredentials] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const result = await login(credentials)
    if (result.success) {
      navigate('/dashboard')
    } else {
      setError(result.message)
    }
    setLoading(false)
  }

  const demoAccounts = [
    { username: 'superadmin', password: 'admin123', role: 'Super Admin' },
    { username: 'schooladmin', password: 'admin123', role: 'School Admin' },
    { username: 'teacher1', password: 'teacher123', role: 'Teacher' },
    { username: 'student1', password: 'student123', role: 'Student' },
    { username: 'parent1', password: 'parent123', role: 'Parent' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-8">
        {/* Left side - Branding */}
        <div className="flex flex-col justify-center space-y-6">
          <div className="text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start mb-4">
              <School className="h-12 w-12 text-green-600 mr-3" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Nigerian School</h1>
                <p className="text-xl text-green-600">Result Portal</p>
              </div>
            </div>
            <p className="text-gray-600 text-lg">
              Comprehensive result management system for primary and secondary schools across Nigeria
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">✨ Key Features</h3>
            <div className="grid grid-cols-1 gap-3">
              <div className="flex items-center space-x-3">
                <Users className="h-5 w-5 text-green-600" />
                <span className="text-gray-700">Multi-role access (Admin, Teacher, Student, Parent)</span>
              </div>
              <div className="flex items-center space-x-3">
                <BarChart3 className="h-5 w-5 text-green-600" />
                <span className="text-gray-700">Automated result computation & grading</span>
              </div>
              <div className="flex items-center space-x-3">
                <FileText className="h-5 w-5 text-green-600" />
                <span className="text-gray-700">Professional report card generation</span>
              </div>
              <div className="flex items-center space-x-3">
                <Trophy className="h-5 w-5 text-green-600" />
                <span className="text-gray-700">Performance analytics & ranking</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login Form */}
        <Card className="w-full max-w-md mx-auto">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Welcome Back</CardTitle>
            <CardDescription>
              Sign in to access your school portal
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={credentials.username}
                  onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  required
                />
              </div>
              
              {error && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertDescription className="text-red-800">{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>

            {/* Demo Accounts */}
            <div className="mt-6 pt-6 border-t">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Demo Accounts:</h4>
              <div className="grid grid-cols-1 gap-2">
                {demoAccounts.map((account, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    className="justify-start text-left"
                    onClick={() => setCredentials({ username: account.username, password: account.password })}
                  >
                    <Badge variant="secondary" className="mr-2 text-xs">
                      {account.role}
                    </Badge>
                    {account.username}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Dashboard Layout Component
function DashboardLayout({ children }) {
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navigation = {
    admin: [
      { name: 'Dashboard', icon: BarChart3, href: '/dashboard' },
      { name: 'Schools', icon: School, href: '/schools' },
      { name: 'Users', icon: Users, href: '/users' },
      { name: 'Classes', icon: BookOpen, href: '/classes' },
      { name: 'Subjects', icon: GraduationCap, href: '/subjects' },
      { name: 'Sessions', icon: Calendar, href: '/sessions' },
      { name: 'Settings', icon: Settings, href: '/settings' }
    ],
    teacher: [
      { name: 'Dashboard', icon: BarChart3, href: '/dashboard' },
      { name: 'My Classes', icon: BookOpen, href: '/classes' },
      { name: 'Enter Results', icon: FileText, href: '/results' },
      { name: 'Students', icon: Users, href: '/students' },
      { name: 'Reports', icon: TrendingUp, href: '/reports' }
    ],
    student: [
      { name: 'Dashboard', icon: BarChart3, href: '/dashboard' },
      { name: 'My Results', icon: FileText, href: '/results' },
      { name: 'Performance', icon: TrendingUp, href: '/performance' },
      { name: 'Profile', icon: User, href: '/profile' }
    ],
    parent: [
      { name: 'Dashboard', icon: BarChart3, href: '/dashboard' },
      { name: 'Children', icon: Users, href: '/children' },
      { name: 'Results', icon: FileText, href: '/results' },
      { name: 'Notifications', icon: Bell, href: '/notifications' }
    ]
  }

  const currentNav = navigation[user?.role] || navigation.student

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-16 px-6 border-b">
          <div className="flex items-center">
            <School className="h-8 w-8 text-green-600" />
            <span className="ml-2 text-lg font-semibold">School Portal</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="mt-6">
          {currentNav.map((item) => (
            <a
              key={item.name}
              href={item.href}
              className="flex items-center px-6 py-3 text-gray-700 hover:bg-green-50 hover:text-green-600 transition-colors"
            >
              <item.icon className="h-5 w-5 mr-3" />
              {item.name}
            </a>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-6 border-t">
          <div className="flex items-center mb-4">
            <div className="h-10 w-10 bg-green-100 rounded-full flex items-center justify-center">
              <User className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="w-full" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="bg-white shadow-sm border-b">
          <div className="flex items-center justify-between h-16 px-6">
            <div className="flex items-center">
              <Button
                variant="ghost"
                size="sm"
                className="lg:hidden mr-2"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-5 w-5" />
              </Button>
              <h1 className="text-xl font-semibold text-gray-900">
                {user?.school_name || 'School Portal'}
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="capitalize">
                {user?.role}
              </Badge>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

// Dashboard Components for different roles
function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const { token } = useAuth()

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiService.getDashboard(token, 'admin')
        if (response.success) {
          setStats(response.data)
        }
      } catch (error) {
        console.error('Failed to fetch admin stats:', error)
      }
    }
    fetchStats()
  }, [token])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Admin Dashboard</h2>
        <p className="text-gray-600">Overview of your school management system</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Students</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_students || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <GraduationCap className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Teachers</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_teachers || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <BookOpen className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Classes</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_classes || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-orange-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Subjects</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_subjects || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Students</CardTitle>
            <CardDescription>Latest student registrations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.recent_students?.map((student, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{student.name}</p>
                    <p className="text-sm text-gray-600">{student.class} • {student.student_id}</p>
                  </div>
                  <Badge variant="outline">New</Badge>
                </div>
              )) || (
                <p className="text-gray-500">No recent students</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common administrative tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <Button className="h-20 flex-col">
                <Users className="h-6 w-6 mb-2" />
                Add User
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <BookOpen className="h-6 w-6 mb-2" />
                New Class
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <GraduationCap className="h-6 w-6 mb-2" />
                Add Subject
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <FileText className="h-6 w-6 mb-2" />
                View Reports
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function TeacherDashboard() {
  const [stats, setStats] = useState(null)
  const { token } = useAuth()

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiService.getDashboard(token, 'teacher')
        if (response.success) {
          setStats(response.data)
        }
      } catch (error) {
        console.error('Failed to fetch teacher stats:', error)
      }
    }
    fetchStats()
  }, [token])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Teacher Dashboard</h2>
        <p className="text-gray-600">Manage your classes and student results</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <BookOpen className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Assigned Classes</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.assigned_classes || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Students</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_students || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-orange-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Results Pending</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.results_pending || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Current Term</CardTitle>
            <CardDescription>
              {stats?.current_term ? 
                `${stats.current_term.name} - ${stats.current_term.session}` : 
                'No active term'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Results Submitted</span>
                <Badge variant="secondary">{stats?.results_submitted || 0}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Results Pending</span>
                <Badge variant="outline">{stats?.results_pending || 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Submissions</CardTitle>
            <CardDescription>Latest result entries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.recent_submissions?.map((submission, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{submission.student_name}</p>
                    <p className="text-sm text-gray-600">
                      {submission.subject_name} • {submission.class_name}
                    </p>
                  </div>
                  <Badge variant="secondary">{submission.total_score}%</Badge>
                </div>
              )) || (
                <p className="text-gray-500">No recent submissions</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StudentDashboard() {
  const [stats, setStats] = useState(null)
  const { token } = useAuth()

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiService.getDashboard(token, 'student')
        if (response.success) {
          setStats(response.data)
        }
      } catch (error) {
        console.error('Failed to fetch student stats:', error)
      }
    }
    fetchStats()
  }, [token])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Student Dashboard</h2>
        <p className="text-gray-600">Track your academic performance and progress</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Current Average</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.current_average || 0}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Trophy className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Class Position</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats?.class_position || 'N/A'}
                  {stats?.total_students && `/${stats.total_students}`}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <BookOpen className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Subjects</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.current_term_subjects || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Student Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Student ID:</span>
                <span className="font-medium">{stats?.student_info?.student_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Class:</span>
                <span className="font-medium">{stats?.student_info?.current_class}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">School:</span>
                <span className="font-medium">{stats?.student_info?.school_name}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Performance</CardTitle>
            <CardDescription>Your performance over recent terms</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.recent_performance?.map((term, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{term.term_name}</p>
                    <p className="text-sm text-gray-600">{term.session_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{term.average_score}%</p>
                    <p className="text-sm text-gray-600">
                      Pos: {term.class_position}/{term.total_students}
                    </p>
                  </div>
                </div>
              )) || (
                <p className="text-gray-500">No performance data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button className="h-20 flex-col">
              <Eye className="h-6 w-6 mb-2" />
              View Results
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <Download className="h-6 w-6 mb-2" />
              Download Report
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <TrendingUp className="h-6 w-6 mb-2" />
              Performance Chart
            </Button>
            <Button variant="outline" className="h-20 flex-col">
              <User className="h-6 w-6 mb-2" />
              Update Profile
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ParentDashboard() {
  const [stats, setStats] = useState(null)
  const { token } = useAuth()

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiService.getDashboard(token, 'parent')
        if (response.success) {
          setStats(response.data)
        }
      } catch (error) {
        console.error('Failed to fetch parent stats:', error)
      }
    }
    fetchStats()
  }, [token])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Parent Dashboard</h2>
        <p className="text-gray-600">Monitor your children's academic progress</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>My Children</CardTitle>
          <CardDescription>Academic overview of your children</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {stats?.children?.map((child, index) => (
              <Card key={index} className="border-l-4 border-l-green-500">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">{child.full_name}</h3>
                      <p className="text-gray-600">{child.current_class}</p>
                      <p className="text-sm text-gray-500">ID: {child.student_id}</p>
                    </div>
                    <Badge variant="secondary">{child.relationship}</Badge>
                  </div>
                  
                  {child.current_performance && (
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Average Score:</span>
                        <span className="font-medium">{child.current_performance.average_score}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Class Position:</span>
                        <span className="font-medium">
                          {child.current_performance.class_position}/{child.current_performance.total_students}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Attendance:</span>
                        <span className="font-medium">
                          {child.current_performance.attendance_present} days
                        </span>
                      </div>
                    </div>
                  )}
                  
                  <div className="mt-4 flex space-x-2">
                    <Button size="sm" className="flex-1">
                      <Eye className="h-4 w-4 mr-2" />
                      View Results
                    </Button>
                    <Button size="sm" variant="outline" className="flex-1">
                      <Download className="h-4 w-4 mr-2" />
                      Download Report
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )) || (
              <p className="text-gray-500 col-span-2">No children found</p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <Button className="h-20 flex-col">
                <FileText className="h-6 w-6 mb-2" />
                View All Results
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <Bell className="h-6 w-6 mb-2" />
                Notifications
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <TrendingUp className="h-6 w-6 mb-2" />
                Performance Trends
              </Button>
              <Button variant="outline" className="h-20 flex-col">
                <Download className="h-6 w-6 mb-2" />
                Download Reports
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>Recent updates about your children</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <Bell className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Results Available</p>
                  <p className="text-xs text-gray-600">First term results are now available for download</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Calendar className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Parent-Teacher Meeting</p>
                  <p className="text-xs text-gray-600">Scheduled for next Friday at 2:00 PM</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Main Dashboard Component
function Dashboard() {
  const { user } = useAuth()

  const renderDashboard = () => {
    switch (user?.role) {
      case 'super_admin':
      case 'school_admin':
        return <AdminDashboard />
      case 'teacher':
        return <TeacherDashboard />
      case 'student':
        return <StudentDashboard />
      case 'parent':
        return <ParentDashboard />
      default:
        return <div>Unknown user role</div>
    }
  }

  return (
    <DashboardLayout>
      {renderDashboard()}
    </DashboardLayout>
  )
}

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App

