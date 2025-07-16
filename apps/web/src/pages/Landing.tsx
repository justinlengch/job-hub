import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Mail,
  TrendingUp,
  BarChart3,
  Brain,
  ArrowRight,
  Chrome,
  CheckCircle,
  Clock,
  FileText,
} from "lucide-react";

const Landing = () => {
  const { signInWithGoogle } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error("Sign in error:", error);
      setIsLoading(false);
    }
  };

  const features = [
    {
      icon: Mail,
      title: "Gmail Integration",
      description:
        "Automatically sync and parse job-related emails from your Gmail inbox",
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      icon: Brain,
      title: "AI-Powered Parsing",
      description:
        "Smart extraction of company names, job titles, and application status",
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      icon: BarChart3,
      title: "Visual Analytics",
      description:
        "Track your application progress with intuitive charts and metrics",
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      icon: TrendingUp,
      title: "Timeline Tracking",
      description:
        "Monitor your job search journey with a comprehensive activity timeline",
      color: "text-yellow-600",
      bgColor: "bg-yellow-100",
    },
  ];

  const benefits = [
    "Never miss a follow-up email again",
    "Automatically organize all job communications",
    "Track application status changes in real-time",
    "Get insights into your job search performance",
    "Stay on top of interview schedules and deadlines",
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">Job Hub</h1>
            </div>
            <Button
              onClick={handleGoogleSignIn}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              <Chrome className="h-4 w-4" />
              {isLoading ? "Signing in..." : "Sign in with Google"}
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Your Gmail-Based
            <span className="text-blue-600"> Job Application Tracker</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Automatically parse job-related emails, track application status,
            and stay organized throughout your job search journey.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              size="lg"
              onClick={handleGoogleSignIn}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              <Chrome className="h-5 w-5" />
              {isLoading ? "Connecting..." : "Get Started with Gmail"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
            Everything you need to track your job search
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="border-0 shadow-sm">
                <CardHeader className="text-center pb-2">
                  <div
                    className={`w-12 h-12 ${feature.bgColor} rounded-lg flex items-center justify-center mx-auto mb-4`}
                  >
                    <feature.icon className={`h-6 w-6 ${feature.color}`} />
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                  <p className="text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Benefits Section */}
        <div className="grid md:grid-cols-2 gap-12 items-center mb-16">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">
              Stay organized and never miss an opportunity
            </h2>
            <div className="space-y-4">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <p className="text-gray-600">{benefit}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Card className="p-6 text-center border-0 shadow-sm">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-1">150+</div>
              <p className="text-sm text-gray-600">Applications Tracked</p>
            </Card>
            <Card className="p-6 text-center border-0 shadow-sm">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-1">98%</div>
              <p className="text-sm text-gray-600">Parsing Accuracy</p>
            </Card>
            <Card className="p-6 text-center border-0 shadow-sm">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <Clock className="h-6 w-6 text-purple-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-1">24/7</div>
              <p className="text-sm text-gray-600">Email Monitoring</p>
            </Card>
            <Card className="p-6 text-center border-0 shadow-sm">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-1">3x</div>
              <p className="text-sm text-gray-600">Faster Organization</p>
            </Card>
          </div>
        </div>

        {/* CTA Section */}
        <Card className="text-center p-12 bg-gradient-to-r from-blue-50 to-purple-50 border-0">
          <CardContent>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Ready to streamline your job search?
            </h2>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Join thousands of job seekers who are staying organized and
              landing their dream jobs with Job Hub.
            </p>
            <Button
              size="lg"
              onClick={handleGoogleSignIn}
              disabled={isLoading}
              className="flex items-center gap-2 mx-auto"
            >
              <Chrome className="h-5 w-5" />
              {isLoading ? "Connecting..." : "Start Tracking Applications"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600">
            <p>&copy; 2025 Job Hub. Built with React, Supabase, and AI.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
