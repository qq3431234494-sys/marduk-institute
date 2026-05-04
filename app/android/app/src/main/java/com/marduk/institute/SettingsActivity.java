package com.marduk.institute;

import android.app.Activity;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.Button;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.view.View;
import android.content.Intent;

public class SettingsActivity extends Activity {

    private EditText urlInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        ScrollView scrollView = new ScrollView(this);
        scrollView.setBackgroundColor(0xFF0b0b14);
        scrollView.setFillViewport(true);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(48, 80, 48, 48);
        layout.setBackgroundColor(0xFF0b0b14);

        TextView title = new TextView(this);
        title.setText("MARDUK INSTITUTE\nServer Configuration");
        title.setTextColor(0xFFff6b2b);
        title.setTextSize(20);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        title.setPadding(0, 0, 0, 40);
        layout.addView(title);

        TextView label = new TextView(this);
        label.setText("Server URL:");
        label.setTextColor(0xFF888888);
        label.setTextSize(14);
        label.setPadding(0, 0, 0, 8);
        layout.addView(label);

        String savedUrl = getSharedPreferences("marduk", MODE_PRIVATE)
                .getString("server_url", "http://10.0.2.2:5000");

        urlInput = new EditText(this);
        urlInput.setText(savedUrl);
        urlInput.setTextColor(0xFFFFFFFF);
        urlInput.setHint("http://your-server:5000");
        urlInput.setHintTextColor(0xFF666666);
        urlInput.setBackgroundColor(0xFF1a1a2e);
        urlInput.setPadding(24, 16, 24, 16);
        urlInput.setTextSize(16);
        urlInput.setSingleLine(true);
        layout.addView(urlInput);

        TextView hint = new TextView(this);
        hint.setText("\n\u2022 Local emulator: http://10.0.2.2:5000\n\u2022 LAN server: http://192.168.x.x:5000\n\u2022 Remote: https://your-domain.com");
        hint.setTextColor(0xFF666666);
        hint.setTextSize(12);
        layout.addView(hint);

        Button saveBtn = new Button(this);
        saveBtn.setText("SAVE & CONNECT");
        saveBtn.setTextColor(0xFF0b0b14);
        saveBtn.setBackgroundColor(0xFFff6b2b);
        saveBtn.setPadding(32, 24, 32, 24);
        saveBtn.setTextSize(16);
        saveBtn.setOnClickListener(v -> {
            String url = urlInput.getText().toString().trim();
            if (!url.isEmpty()) {
                getSharedPreferences("marduk", MODE_PRIVATE)
                        .edit()
                        .putString("server_url", url)
                        .apply();
                Intent intent = new Intent(SettingsActivity.this, MainActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(intent);
                finish();
            }
        });

        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        btnParams.topMargin = 40;
        saveBtn.setLayoutParams(btnParams);
        layout.addView(saveBtn);

        scrollView.addView(layout);
        setContentView(scrollView);
    }
}
