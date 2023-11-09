/*
 * Copyright (c) 2021 Keystone
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * in the file COPYING.  If not, see <http://www.gnu.org/licenses/>.
 */

package com.keystone.cold.ui;

import android.os.Bundle;

import com.keystone.cold.R;
import com.keystone.cold.config.FeatureFlags;
import com.keystone.cold.ui.common.FullScreenActivity;

public class SplashActivity extends FullScreenActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (FeatureFlags.ENABLE_REMOVE_WALLET_MODE) {
            setContentView(R.layout.activity_splash_remove_wallet_mode);
        } else {
            setContentView(R.layout.activity_splash);
        }
    }
}
