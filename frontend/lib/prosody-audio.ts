type Sample = {
  file: string;
  words: number[];
  contour: [seconds: number, hertz: number][];
};

// Word offsets are aligned to the six bundled samples. Contours are sampled
// from their voiced regions and use a common pitch scale in the lesson.
export const samples: Sample[][] = [
  [
    {
      file: "about",
      words: [0.12, 0.24],
      contour: [
        [0.12, 186],
        [0.19, 172],
        [0.26, 167],
        [0.34, 165],
        [0.41, 150],
        [0.49, 147],
      ],
    },
  ],
  [
    {
      file: "focus-you",
      words: [0.13, 0.35, 0.6, 0.88],
      contour: [
        [0.19, 195],
        [0.26, 213],
        [0.41, 225],
        [0.49, 232],
        [0.56, 216],
        [0.64, 208],
        [0.71, 235],
        [0.79, 242],
        [0.94, 211],
        [1.01, 176],
        [1.09, 258],
        [1.16, 242],
      ],
    },
    {
      file: "focus-think",
      words: [0.13, 0.35, 0.6, 0.88],
      contour: [
        [0.19, 195],
        [0.26, 213],
        [0.41, 225],
        [0.49, 232],
        [0.56, 216],
        [0.64, 203],
        [0.71, 229],
        [0.79, 235],
        [0.94, 216],
        [1.01, 172],
        [1.09, 262],
        [1.16, 239],
      ],
    },
  ],
  [
    {
      file: "really-up",
      words: [0.12, 0.34],
      contour: [
        [0.12, 184],
        [0.19, 180],
        [0.26, 176],
        [0.34, 163],
        [0.41, 174],
        [0.49, 188],
        [0.56, 200],
      ],
    },
    {
      file: "really-down",
      words: [0.12, 0.34],
      contour: [
        [0.12, 184],
        [0.19, 180],
        [0.26, 180],
        [0.34, 158],
        [0.41, 145],
        [0.49, 140],
        [0.56, 151],
      ],
    },
  ],
  [
    {
      file: "take-seat",
      words: [0.12, 0.59],
      contour: [
        [0.19, 219],
        [0.26, 219],
        [0.41, 219],
        [0.64, 229],
        [0.71, 195],
        [0.79, 155],
      ],
    },
  ],
];
