"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

/**
 * 사용자 정보 타입
 */
export interface User {
  id: number;
  email: string;
  nickname: string;
  role: "user" | "admin";
  is_active: boolean;
}

/**
 * 인증 컨텍스트 타입
 */
interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

/**
 * 인증 컨텍스트 생성
 */
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * 인증 컨텍스트 프로바이더 Props
 */
interface AuthProviderProps {
  children: ReactNode;
}

/**
 * 인증 컨텍스트 프로바이더
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * 로그인 함수
   */
  const login = async (email: string, password: string) => {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // 쿠키 포함
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "로그인 실패");
    }

    const data = await response.json();
    setUser(data.user);
  };

  /**
   * 로그아웃 함수
   */
  const logout = async () => {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include", // 쿠키 포함
    });

    if (!response.ok) {
      throw new Error("로그아웃 실패");
    }

    setUser(null);
  };

  /**
   * 인증 상태 확인 함수
   */
  const checkAuth = async () => {
    try {
      const response = await fetch("/api/auth/check", {
        credentials: "include", // 쿠키 포함
      });

      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
        } else {
          setUser(null);
        }
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error("인증 확인 실패:", error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 컴포넌트 마운트 시 인증 상태 확인
   */
  useEffect(() => {
    checkAuth();
  }, []);

  /**
   * 계산된 속성: 인증 여부
   */
  const isAuthenticated = user !== null;

  /**
   * 계산된 속성: 관리자 여부
   */
  const isAdmin = user?.role === "admin";

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    checkAuth,
    isAuthenticated,
    isAdmin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * 인증 컨텍스트 Hook
 *
 * @returns AuthContextType
 * @throws Error if used outside AuthProvider
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
