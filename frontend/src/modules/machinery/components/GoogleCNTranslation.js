/* @flow */

import React from 'react';
import { Localized } from '@fluent/react';

/**
 * Show the translation source from Google CN Translate.
 */
export default function GoogleCNTranslation() {
    return (
        <li>
            <Localized
                id='machinery-GoogleCNTranslation--visit-google'
                attrs={{ title: true }}
            >
                <a
                    className='translation-source'
                    href='https://translate.google.cn/'
                    title='Visit Google CN Translate'
                    target='_blank'
                    rel='noopener noreferrer'
                    onClick={(e: SyntheticMouseEvent<>) => e.stopPropagation()}
                >
                    <span>Google CN Translate</span>
                </a>
            </Localized>
        </li>
    );
}
