// 공개 학교 검색 결과의 학교급·시도 표기만 정규화한다.
export const SCHOOL_KIND_REV: Record<string, string> = {
  "02": "초등학교", "03": "중학교", "04": "고등학교",
  "05": "특수학교", "06": "그외학교", "07": "각종학교",
};

const SIDO_ALIAS: Record<string, string> = {
  서울: "서울특별시", 부산: "부산광역시", 대구: "대구광역시", 인천: "인천광역시",
  광주: "광주광역시", 대전: "대전광역시", 울산: "울산광역시", 세종: "세종특별자치시",
  경기: "경기도", 강원: "강원특별자치도", 충북: "충청북도", 충남: "충청남도",
  전북: "전북특별자치도", 전남: "전라남도", 경북: "경상북도", 경남: "경상남도",
  제주: "제주특별자치도", 강원도: "강원특별자치도", 전라북도: "전북특별자치도",
  제주도: "제주특별자치도",
};

export function normalizeSido(value: string): string {
  const name = value.trim();
  return SIDO_ALIAS[name] ?? name;
}
