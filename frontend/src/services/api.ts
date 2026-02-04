import type { AnalysisData, HistoryIndex, KISGeminiData, KISAnalysisData } from './types';

const BASE_URL = import.meta.env.DEV ? '' : '.';

export async function fetchLatestData(): Promise<AnalysisData> {
  const response = await fetch(`${BASE_URL}/results/vision/vision_analysis.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch latest data');
  }
  return response.json();
}

export async function fetchHistoryData(filename: string): Promise<AnalysisData> {
  const response = await fetch(`${BASE_URL}/results/vision/history/${filename}`);
  if (!response.ok) {
    throw new Error('Failed to fetch history data');
  }
  return response.json();
}

export async function fetchHistoryIndex(): Promise<HistoryIndex> {
  const response = await fetch(`${BASE_URL}/results/vision/history_index.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch history index');
  }
  return response.json();
}

// KIS API 데이터 fetch 함수들 (404 시 null 반환)
export async function fetchKISData(): Promise<KISGeminiData | null> {
  try {
    // kis_gemini.json은 Gemini 분석용으로 변환된 데이터 (stocks 키 포함)
    const response = await fetch(`${BASE_URL}/results/kis/kis_gemini.json`);
    if (!response.ok) {
      if (response.status === 404) {
        return null; // 파일이 없으면 null 반환 (에러 아님)
      }
      throw new Error('Failed to fetch KIS data');
    }
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchKISAnalysis(): Promise<KISAnalysisData | null> {
  try {
    const response = await fetch(`${BASE_URL}/results/kis/kis_analysis.json`);
    if (!response.ok) {
      if (response.status === 404) {
        return null; // 파일이 없으면 null 반환 (에러 아님)
      }
      throw new Error('Failed to fetch KIS analysis');
    }
    return response.json();
  } catch {
    return null;
  }
}

// KIS 히스토리 API 함수들
export async function fetchKISHistoryIndex(): Promise<HistoryIndex | null> {
  try {
    const response = await fetch(`${BASE_URL}/results/kis/history_index.json`);
    if (!response.ok) {
      if (response.status === 404) {
        return null;
      }
      throw new Error('Failed to fetch KIS history index');
    }
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchKISHistoryData(filename: string): Promise<KISAnalysisData | null> {
  try {
    const response = await fetch(`${BASE_URL}/results/kis/history/${filename}`);
    if (!response.ok) {
      if (response.status === 404) {
        return null;
      }
      throw new Error('Failed to fetch KIS history data');
    }
    return response.json();
  } catch {
    return null;
  }
}
