export {};

declare global {
  interface Array<T> {
    reduce(
      callbackfn: (
        previousValue: number,
        currentValue: T,
        currentIndex: number,
        array: T[],
      ) => number,
      initialValue: number,
    ): number;
  }
}
