import { ChevronRight } from 'lucide-react';
import { Fragment } from 'react';

export type ReviewStepKey = 'literature' | 'science' | 'audience';

type ReviewProgressProps = {
  currentStep: ReviewStepKey;
  literatureDone?: boolean;
  scienceDone?: boolean;
  audienceDone?: boolean;
  onStepClick?: (step: ReviewStepKey) => void;
};

const STEP_CONFIG = [
  {
    key: 'literature' as ReviewStepKey,
    icon: '📚',
    title: '文学家审校',
    desc: '审校文学性、语言表达和叙事结构',
  },
  {
    key: 'science' as ReviewStepKey,
    icon: '🔬',
    title: '科学家审校',
    desc: '审校科学准确性和知识点正确性',
  },
  {
    key: 'audience' as ReviewStepKey,
    icon: '🧒',
    title: '观众反馈/编辑校对',
    desc: '根据观众反馈进行编辑校对，确保适合目标受众理解',
  },
];

function isStepDone(
  key: ReviewStepKey,
  doneMap: Record<ReviewStepKey, boolean>,
  currentStep: ReviewStepKey,
) {
  const currentIndex = STEP_CONFIG.findIndex((step) => step.key === currentStep);
  const stepIndex = STEP_CONFIG.findIndex((step) => step.key === key);
  return doneMap[key] || stepIndex < currentIndex;
}

export default function ReviewProgress({
  currentStep,
  literatureDone = false,
  scienceDone = false,
  audienceDone = false,
  onStepClick,
}: ReviewProgressProps) {
  const doneMap: Record<ReviewStepKey, boolean> = {
    literature: literatureDone,
    science: scienceDone,
    audience: audienceDone,
  };

  return (
    <div className="mb-6 rounded-2xl border border-[#E8E5DF] bg-[#FCFBF8] p-5">
      <div className="mb-5">
        <h3 className="text-xl font-bold text-gray-900">审校进度</h3>
        <p className="text-sm text-gray-500">顺序审核模式：文学家 - 科学家 - 观众反馈/编辑校对</p>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-center">
        {STEP_CONFIG.map((step, index) => {
          const done = isStepDone(step.key, doneMap, currentStep);
          const active = step.key === currentStep;
          const canClick = done;
          const lockHint =
            step.key === 'science'
              ? '请先完成文学家审校'
              : step.key === 'audience'
              ? '请先完成科学家审校'
              : '当前步骤未解锁';

          return (
            <Fragment key={step.key}>
              <div className="group relative">
                <button
                  type="button"
                  onClick={() => {
                    if (canClick && onStepClick) {
                      onStepClick(step.key);
                    }
                  }}
                  disabled={!canClick}
                  className={[
                    'text-center rounded-xl p-2 transition-colors',
                    canClick ? 'cursor-pointer hover:bg-[#FFF4E8]' : 'cursor-not-allowed opacity-60',
                  ].join(' ')}
                  aria-disabled={!canClick}
                  title={canClick ? `回看${step.title}` : `请先完成前序步骤后解锁${step.title}`}
                >
                  <div
                    className={[
                      'mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full border text-3xl transition-colors',
                      active
                        ? 'border-[#F7A84A] bg-[#FFE1BE]'
                        : done
                        ? 'border-[#F6D5AA] bg-[#FFF2DF]'
                        : 'border-[#E8E5DF] bg-[#F2F0EB] grayscale',
                    ].join(' ')}
                  >
                    {step.icon}
                  </div>

                  <h4 className={['text-base', 'font-bold', active ? 'text-gray-900' : 'text-gray-700'].join(' ')}>{step.title}</h4>
                  <p className="mt-1 text-sm text-gray-500">{step.desc}</p>
                </button>

                {!canClick ? (
                  <div className="pointer-events-none absolute left-1/2 top-0 z-20 hidden -translate-x-1/2 -translate-y-[110%] whitespace-nowrap rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg group-hover:block group-focus-within:block">
                    {lockHint}
                    <div className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-gray-900" />
                  </div>
                ) : null}
                </div>

              {index < STEP_CONFIG.length - 1 ? (
                <div className="hidden justify-center md:flex" aria-hidden="true">
                  <ChevronRight className="text-gray-400" size={28} />
                </div>
              ) : null}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
